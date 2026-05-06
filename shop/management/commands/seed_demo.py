from decimal import Decimal

from django.core.management.base import BaseCommand

from shop.models import Product


class Command(BaseCommand):
    help = "Creates demo products for local testing."

    def handle(self, *args, **options):
        products = [
            ("Laptop Stand", "Aluminum stand for a desk setup", Decimal("29.99"), 50),
            ("Wireless Mouse", "Ergonomic mouse with USB receiver", Decimal("18.50"), 80),
            ("Mechanical Keyboard", "Compact keyboard for programmers", Decimal("64.00"), 30),
        ]

        for name, description, price, stock in products:
            Product.objects.update_or_create(
                name=name,
                defaults={
                    "description": description,
                    "price": price,
                    "stock_quantity": stock,
                },
            )

        self.stdout.write(self.style.SUCCESS("Demo products are ready"))
