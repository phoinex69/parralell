import json
from decimal import Decimal

from django.test import Client, TestCase, override_settings

from .models import BackgroundTask, Order, Product
from .tasks import process_next_task


@override_settings(ROOT_URLCONF="commerce_engine.urls")
class CheckoutTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(
            name="Test Keyboard",
            description="Demo product",
            price=Decimal("10.00"),
            stock_quantity=2,
        )

    def test_checkout_reduces_stock_and_creates_background_tasks(self):
        response = self.client.post(
            "/api/checkout/",
            data=json.dumps(
                {
                    "customer_email": "student@example.com",
                    "items": [{"product_id": self.product.id, "quantity": 1}],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(BackgroundTask.objects.count(), 2)

    def test_checkout_rejects_oversell(self):
        payload = {
            "customer_email": "student@example.com",
            "items": [{"product_id": self.product.id, "quantity": 3}],
        }

        response = self.client.post(
            "/api/checkout/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 2)
        self.assertEqual(Order.objects.count(), 0)

    def test_worker_processes_queued_task_outside_request_flow(self):
        self.client.post(
            "/api/checkout/",
            data=json.dumps(
                {
                    "customer_email": "student@example.com",
                    "items": [{"product_id": self.product.id, "quantity": 1}],
                }
            ),
            content_type="application/json",
        )

        processed = process_next_task()

        self.assertTrue(processed)
        self.assertEqual(
            BackgroundTask.objects.filter(status=BackgroundTask.Status.DONE).count(),
            1,
        )
