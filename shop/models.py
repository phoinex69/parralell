from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Product(TimeStampedModel):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField()
    version = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.stock_quantity} in stock)"


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    customer_email = models.EmailField()
    status = models.CharField(max_length=20, choices=Status, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Order #{self.pk} - {self.customer_email}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)


class BackgroundTask(TimeStampedModel):
    class Kind(models.TextChoices):
        EMAIL = "email", "Email notification"
        INVOICE = "invoice", "Invoice generation"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    kind = models.CharField(max_length=30, choices=Kind)
    status = models.CharField(max_length=20, choices=Status, default=Status.QUEUED)
    payload = models.JSONField(default=dict)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]
