from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TransactionTestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import Order, Product
from .services import CheckoutLine, OutOfStockError, create_order


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class CheckoutApiTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="student123",
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.product = Product.objects.create(
            name="Test Keyboard",
            description="Demo product",
            price=Decimal("10.00"),
            stock_quantity=2,
        )

    @patch("shop.tasks.log_order_analytics.delay")
    @patch("shop.tasks.generate_invoice.delay")
    @patch("shop.tasks.send_order_confirmation.delay")
    def test_checkout_reduces_stock_and_queues_celery_tasks(
        self,
        send_email,
        generate_invoice,
        log_analytics,
    ):
        response = self.client.post(
            "/api/checkout/",
            data={"items": [{"product_id": self.product.id, "quantity": 1}]},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)
        self.assertEqual(Order.objects.count(), 1)
        send_email.assert_called_once()
        generate_invoice.assert_called_once()
        log_analytics.assert_called_once()

    @patch("shop.tasks.log_order_analytics.delay")
    @patch("shop.tasks.generate_invoice.delay")
    @patch("shop.tasks.send_order_confirmation.delay")
    def test_checkout_rejects_oversell_and_rolls_back_tasks(
        self,
        send_email,
        generate_invoice,
        log_analytics,
    ):
        response = self.client.post(
            "/api/checkout/",
            data={"items": [{"product_id": self.product.id, "quantity": 3}]},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 2)
        self.assertEqual(Order.objects.count(), 0)
        send_email.assert_not_called()
        generate_invoice.assert_not_called()
        log_analytics.assert_not_called()

    @patch("shop.tasks.log_order_analytics.delay")
    @patch("shop.tasks.generate_invoice.delay")
    @patch("shop.tasks.send_order_confirmation.delay")
    def test_service_prevents_last_item_being_sold_twice(
        self,
        send_email,
        generate_invoice,
        log_analytics,
    ):
        self.product.stock_quantity = 1
        self.product.save(update_fields=["stock_quantity"])

        create_order(
            user=self.user,
            lines=[CheckoutLine(product_id=self.product.id, quantity=1)],
        )

        with self.assertRaises(OutOfStockError):
            create_order(
                user=self.user,
                lines=[CheckoutLine(product_id=self.product.id, quantity=1)],
            )

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 0)
        self.assertEqual(Order.objects.count(), 1)
        send_email.assert_called_once()
        generate_invoice.assert_called_once()
        log_analytics.assert_called_once()
