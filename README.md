# High-Performance E-Commerce Backend Engine

This is a Django student project for the Spring 2026 Parallel Programming course.
The current version implements only the first three non-functional requirements,
while keeping the structure ready for caching, batch jobs, load balancing, and
stress testing later.

## What The Project Means

The course project is not mainly about building many shopping features. It is
about proving that the backend stays correct and stable when many users use it
at the same time.

The full project asks for:

1. Correct concurrent access to shared data such as product stock.
2. Resource management so the server does not accept unlimited work.
3. Asynchronous processing for slow tasks such as emails and invoices.
4. Batch processing for large jobs such as daily sales reports.
5. Load balancing across multiple server instances.
6. Distributed caching, usually with Redis.
7. Explicit locking strategy for sensitive updates.
8. ACID transactions for operations that must fully succeed or fail.
9. Stress testing with at least 100 concurrent users.
10. Benchmarking and bottleneck analysis before and after optimization.

This submission starts with requirements 1, 2, and 3.

## Current Architecture

`commerce_engine` is the Django project. `shop` is the e-commerce app.

Main modules:

- `shop.models`: products, orders, order items, and background task records.
- `shop.services`: checkout business logic and inventory synchronization.
- `shop.middleware`: request capacity control.
- `shop.tasks`: background task processing.
- `shop.management.commands.process_tasks`: worker command for async jobs.
- `shop.views`: small JSON API.

## Requirement 1: Concurrent Access And Data Integrity

The sensitive resource is `Product.stock_quantity`.

Checkout uses `transaction.atomic()` so order creation, inventory update, order
items, and background task creation are one unit of work. If any step fails, the
database rolls back.

The synchronization point is in `shop/services.py`:

```python
Product.objects.filter(
    id=line.product_id,
    stock_quantity__gte=line.quantity,
).update(
    stock_quantity=F("stock_quantity") - line.quantity,
    version=F("version") + 1,
)
```

This is an atomic conditional database update. If two users try to buy the last
item at the same time, only one update can succeed. The other request receives a
`409 Conflict` response instead of creating an invalid order.

`select_for_update()` is also present in the checkout query. SQLite ignores this,
but PostgreSQL will use it as a pessimistic row lock in the future without
rewriting the service design.

## Requirement 2: Resource Management And Capacity Control

`shop.middleware.CapacityControlMiddleware` uses a bounded semaphore. The server
accepts only `MAX_CONCURRENT_REQUESTS` requests at the same time. If the limit is
full for longer than `CAPACITY_WAIT_SECONDS`, the request returns HTTP `503`.

This prevents the local server from consuming unlimited threads or database
connections under load. The values are currently configured in
`commerce_engine/settings.py`:

```python
MAX_CONCURRENT_REQUESTS = 20
CAPACITY_WAIT_SECONDS = 2
```

These numbers can be changed during benchmarking.

## Requirement 3: Asynchronous Processing

Checkout should not wait for emails or invoices. Instead, it inserts rows into
`BackgroundTask` during the transaction. A separate worker processes those rows:

```powershell
python manage.py process_tasks
```

For a one-time demo:

```powershell
python manage.py process_tasks --once
```

This is intentionally a simple database-backed queue for student clarity. Later,
it can be replaced with Celery and Redis while keeping the same idea: the HTTP
request creates work, and workers perform the slow work outside the request.

## Run Locally

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open:

- `GET /api/products/`
- `POST /api/checkout/`
- `GET /api/tasks/`

Checkout example:

```json
{
  "customer_email": "student@example.com",
  "items": [
    {"product_id": 1, "quantity": 2}
  ]
}
```

## Future Expansion

The next requirements can be added without replacing the current design:

- Redis cache around product reads in `shop.views.product_list`.
- Batch sales aggregation as another management command.
- Load balancing by running multiple Django instances behind Nginx or a simple
  round-robin reverse proxy.
- Stress testing with Locust or JMeter.
- AOP-style performance monitoring by adding middleware/decorators that measure
  request and service execution time without mixing timing code into business
  logic.
