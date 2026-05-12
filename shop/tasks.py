import logging
import time

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from .models import Order


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_order_confirmation(self, order_id: int) -> dict:
    try:
        order = Order.objects.get(id=order_id)
        time.sleep(1)
        logger.info("Sent confirmation email for order %s to %s", order.id, order.customer_email)
        return {"order_id": order.id, "email": order.customer_email, "sent": True}
    except SoftTimeLimitExceeded:
        logger.warning("Email task timed out for order %s", order_id)
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_invoice(self, order_id: int) -> dict:
    try:
        order = Order.objects.prefetch_related("items").get(id=order_id)
        time.sleep(2)
        logger.info("Generated invoice for order %s", order.id)
        return {
            "order_id": order.id,
            "total_amount": str(order.total_amount),
            "item_count": order.items.count(),
        }
    except SoftTimeLimitExceeded:
        logger.warning("Invoice task timed out for order %s", order_id)
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def log_order_analytics(self, order_id: int) -> dict:
    order = Order.objects.get(id=order_id)
    logger.info("Analytics event recorded for paid order %s", order.id)
    return {"event": "order_paid", "order_id": order.id}
