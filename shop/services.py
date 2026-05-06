from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.db.models import F

from .models import BackgroundTask, Order, OrderItem, Product


class OutOfStockError(Exception):
    pass


@dataclass(frozen=True)
class CheckoutLine:
    product_id: int
    quantity: int


def create_order(customer_email: str, lines: list[CheckoutLine]) -> Order:
    if not lines:
        raise ValueError("checkout requires at least one item")

    normalized_lines = _merge_duplicate_lines(lines)

    with transaction.atomic():
        product_ids = [line.product_id for line in normalized_lines]
        products = {
            product.id: product
            for product in Product.objects.select_for_update().filter(id__in=product_ids)
        }

        missing = sorted(set(product_ids) - set(products))
        if missing:
            raise ValueError(f"unknown product ids: {missing}")

        total = Decimal("0.00")
        for line in normalized_lines:
            if line.quantity <= 0:
                raise ValueError("quantity must be greater than zero")

            # Synchronization point:
            # This conditional UPDATE is atomic in the database. Under concurrent
            # checkout requests, exactly one transaction can consume each stock unit.
            updated = Product.objects.filter(
                id=line.product_id,
                stock_quantity__gte=line.quantity,
            ).update(
                stock_quantity=F("stock_quantity") - line.quantity,
                version=F("version") + 1,
            )
            if updated == 0:
                product = products[line.product_id]
                raise OutOfStockError(
                    f"not enough stock for {product.name}: requested {line.quantity}"
                )

            total += products[line.product_id].price * line.quantity

        order = Order.objects.create(
            customer_email=customer_email,
            status=Order.Status.PAID,
            total_amount=total,
        )

        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=products[line.product_id],
                    quantity=line.quantity,
                    unit_price=products[line.product_id].price,
                )
                for line in normalized_lines
            ]
        )

        BackgroundTask.objects.bulk_create(
            [
                BackgroundTask(
                    kind=BackgroundTask.Kind.EMAIL,
                    payload={"order_id": order.id, "email": customer_email},
                ),
                BackgroundTask(
                    kind=BackgroundTask.Kind.INVOICE,
                    payload={"order_id": order.id},
                ),
            ]
        )

    return order


def _merge_duplicate_lines(lines: list[CheckoutLine]) -> list[CheckoutLine]:
    quantities: dict[int, int] = {}
    for line in lines:
        quantities[line.product_id] = quantities.get(line.product_id, 0) + line.quantity
    return [
        CheckoutLine(product_id=product_id, quantity=quantity)
        for product_id, quantity in quantities.items()
    ]
