import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import BackgroundTask, Order, Product
from .services import CheckoutLine, OutOfStockError, create_order


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@require_GET
def product_list(request):
    products = Product.objects.order_by("id")
    return JsonResponse({"products": [_product_to_dict(product) for product in products]})


@require_GET
def product_detail(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({"error": "product not found"}, status=404)

    return JsonResponse({"product": _product_to_dict(product)})


@csrf_exempt
@require_POST
def checkout(request):
    try:
        body = json.loads(request.body or "{}")
        lines = [
            CheckoutLine(product_id=int(item["product_id"]), quantity=int(item["quantity"]))
            for item in body.get("items", [])
        ]
        order = create_order(customer_email=body["customer_email"], lines=lines)
    except KeyError as exc:
        return JsonResponse({"error": f"missing field: {exc.args[0]}"}, status=400)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except OutOfStockError as exc:
        return JsonResponse({"error": str(exc)}, status=409)

    return JsonResponse(
        {
            "order": _order_to_dict(order),
            "queued_background_tasks": ["email", "invoice"],
        },
        status=201,
    )


@require_GET
def task_list(request):
    tasks = BackgroundTask.objects.order_by("-created_at")[:50]
    return JsonResponse(
        {
            "tasks": [
                {
                    "id": task.id,
                    "kind": task.kind,
                    "status": task.status,
                    "attempts": task.attempts,
                    "payload": task.payload,
                    "last_error": task.last_error,
                }
                for task in tasks
            ]
        }
    )


def _product_to_dict(product):
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": str(product.price),
        "stock_quantity": product.stock_quantity,
        "version": product.version,
    }


def _order_to_dict(order):
    saved_order = Order.objects.prefetch_related("items__product").get(id=order.id)
    return {
        "id": saved_order.id,
        "customer_email": saved_order.customer_email,
        "status": saved_order.status,
        "total_amount": str(saved_order.total_amount),
        "items": [
            {
                "product_id": item.product_id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
            }
            for item in saved_order.items.all()
        ],
    }
