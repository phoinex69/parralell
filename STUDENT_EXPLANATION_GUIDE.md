# Student Explanation Guide

# High-Performance E-Commerce Backend Engine

This document explains the project step by step in simple terms. The goal is to
help you understand it well enough to explain it as your own university project.

## 1. What This Project Is

This is a backend-only e-commerce project built with Django.

It does not have a frontend. Users interact with it through JSON APIs using
Postman, PowerShell, or any HTTP client.

The project supports:

- user registration
- user login
- product listing
- checkout
- order creation
- stock reduction
- background jobs such as email, invoice, and analytics simulation

The main purpose is not shopping features. The main purpose is showing parallel
programming and backend concepts:

- safe concurrent access
- race condition prevention
- asynchronous processing
- resource control
- queue workers
- Redis usage

## 2. Technologies Used

### Django

Django is the main backend framework.

I used it because it gives:

- project structure
- database models
- migrations
- URL routing
- settings
- admin panel
- tests
- transaction support

This simplified the project because I did not need to manually build a web
server, database layer, or routing system.

### Django REST Framework

Django REST Framework, usually called DRF, is used to build JSON APIs.

I used it because it gives:

- API views
- serializers
- validation
- authentication support
- throttling
- clean JSON responses

This makes the API easier to explain because each request has a serializer that
checks if the input is valid.

### Celery

Celery is used for background jobs.

I used it because checkout should not wait for slow tasks like:

- sending an email
- generating an invoice
- logging analytics

Instead, checkout finishes quickly, then Celery workers process those tasks
later.

### Redis

Redis is used in two ways:

1. As the Celery message broker.
2. As the Django cache backend.

As a message broker, Redis stores background jobs until a Celery worker takes
them.

As a cache, Redis stores product list responses temporarily so the database does
not need to be queried every time.

### django-celery-results

This library stores Celery task results in the database.

It helps you see if a background task succeeded, failed, retried, or is still
pending.

### django-redis

This connects Django's cache system to Redis.

It lets the code use simple functions like:

```python
cache.get(...)
cache.set(...)
cache.delete(...)
```

without manually writing Redis commands.

### psycopg2-binary

This is the PostgreSQL driver for Django.

SQLite can run the project locally, but PostgreSQL is better for the final
concurrency demonstration because it supports real row-level locks.

### gunicorn

Gunicorn is a production WSGI server.

The development server is enough for local testing, but Gunicorn is included to
show how the backend could run in a more production-like environment.

### flower

Flower is optional monitoring for Celery.

It gives a browser dashboard to see workers, queues, tasks, retries, and
failures.

## 3. Project Structure

The project has one Django project and one Django app.

```text
commerce_engine/
```

This is the Django project. It contains global configuration.

Important files:

```text
commerce_engine/settings.py
commerce_engine/urls.py
commerce_engine/celery.py
```

```text
shop/
```

This is the e-commerce app.

Important files:

```text
shop/models.py
shop/serializers.py
shop/views.py
shop/services.py
shop/tasks.py
shop/middleware.py
shop/urls.py
shop/tests.py
```

## 4. How I Built It

I built it in this order:

1. Created a Django project named `commerce_engine`.
2. Created one app named `shop`.
3. Added database models for products, orders, and order items.
4. Added DRF so APIs return JSON.
5. Added serializers to validate request data.
6. Added register and login APIs using Django's built-in user system.
7. Added product APIs.
8. Added checkout logic in a separate service function.
9. Added database transactions and row locking for stock safety.
10. Added Celery and Redis for background processing.
11. Added Celery tasks for email, invoice, and analytics simulation.
12. Added Redis caching for product reads.
13. Added throttling and capacity middleware for overload protection.
14. Added tests.
15. Added a command to simulate many users buying the same product.
16. Added documentation.

I kept everything in one app because this is a university project. Splitting it
into many services would make it harder to explain without improving the core
parallel programming idea.

## 5. Database Models

### Product

Defined in:

```text
shop/models.py
```

Product contains:

- name
- description
- price
- stock_quantity
- version

The most important field is:

```text
stock_quantity
```

This is the shared resource. Many users may try to update it at the same time.

### Order

Order stores the checkout result.

It contains:

- user
- customer_email
- status
- total_amount
- created_at
- updated_at

### OrderItem

OrderItem stores each product inside an order.

It contains:

- order
- product
- quantity
- unit_price

I store `unit_price` because product prices may change later, but old orders
should keep the price from the time of purchase.

## 6. API Layer

The API code is mainly in:

```text
shop/views.py
shop/serializers.py
shop/urls.py
```

### URLs

`shop/urls.py` maps paths to views.

Example:

```text
POST /api/checkout/
```

goes to:

```python
CheckoutView
```

### Views

Views receive HTTP requests and return JSON responses.

Views should not contain complicated business logic. For example, the checkout
view only validates the request and calls:

```python
create_order(...)
```

### Serializers

Serializers check request data.

Example:

```json
{
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    }
  ]
}
```

The checkout serializer checks that:

- `items` exists
- each product ID is positive
- each quantity is positive
- quantity is not too large

This keeps bad data away from the service logic.

## 7. Register And Login

The project uses Django's built-in `User` model.

This avoids building a complicated authentication system.

### Register

Endpoint:

```text
POST /api/auth/register/
```

Request:

```json
{
  "username": "sara",
  "email": "sara@example.com",
  "password": "student123"
}
```

Response:

```json
{
  "user": {
    "id": 3,
    "username": "sara",
    "email": "sara@example.com"
  },
  "token": "generated-token"
}
```

The token is used for authenticated requests.

### Login

Endpoint:

```text
POST /api/auth/login/
```

Request:

```json
{
  "username": "student",
  "password": "student123"
}
```

Response:

```json
{
  "token": "generated-token"
}
```

Use this token in Postman:

```text
Authorization: Token generated-token
```

## 8. Product Listing

Endpoint:

```text
GET /api/products/
```

This returns all products.

The view first checks Redis cache:

```python
cache.get("products:list")
```

If the list is cached, Django returns it quickly.

If it is not cached, Django reads from the database and then stores the response
in Redis for 30 seconds.

This demonstrates caching without making the project complicated.

## 9. Checkout Flow

Endpoint:

```text
POST /api/checkout/
```

Requires authentication.

Request:

```json
{
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    }
  ]
}
```

The checkout flow is:

1. User sends checkout request.
2. DRF checks the token.
3. Serializer validates the item list.
4. View converts items into `CheckoutLine` objects.
5. View calls `create_order(...)` in `shop/services.py`.
6. Service starts a database transaction.
7. Service locks product rows using `select_for_update()`.
8. Service checks stock.
9. Service decreases stock.
10. Service creates order.
11. Service creates order items.
12. Transaction commits.
13. Celery tasks are queued.
14. API returns order JSON.

## 10. Why Race Conditions Happen

A race condition happens when two operations depend on timing.

Example:

```text
Stock = 1
User A reads stock = 1
User B reads stock = 1
User A creates order
User B creates order
```

Both users think stock is available.

This can cause overselling.

## 11. How The Project Prevents Race Conditions

The important code is in:

```text
shop/services.py
```

The checkout service uses:

```python
with transaction.atomic():
```

This means the database operations are one unit. They all succeed or all fail.

It also uses:

```python
Product.objects.select_for_update()
```

This locks the selected product rows until the transaction finishes.

In simple terms:

```text
First checkout locks the product.
Second checkout must wait.
First checkout reduces stock and commits.
Second checkout reads the new stock.
If stock is gone, second checkout fails safely.
```

That is why the project does not sell the last item twice.

## 12. Rollback Handling

If checkout fails, the transaction rolls back.

For example, if stock is not enough:

```python
raise OutOfStockError(...)
```

Because this happens inside `transaction.atomic()`, Django cancels the database
changes.

So the system does not create:

- a wrong order
- wrong order items
- wrong stock value
- background tasks for a failed order

## 13. Why transaction.on_commit Is Used

Background tasks are queued using:

```python
transaction.on_commit(...)
```

This means Celery tasks are sent only after the order is successfully saved.

Without this, a Celery worker might receive an order ID before the transaction is
finished. That could cause the worker to search for an order that does not exist
yet.

This is a small but professional correctness detail.

## 14. Asynchronous Processing

The project has three Celery tasks:

```text
send_order_confirmation
generate_invoice
log_order_analytics
```

They are in:

```text
shop/tasks.py
```

These tasks simulate slow work.

Checkout should not wait for them. Checkout only queues them.

The Celery worker runs separately and processes them in the background.

## 15. How Celery And Redis Work Together

The flow is:

```text
Django creates task
Task is stored in Redis queue
Celery worker takes task from Redis
Worker executes task
Result is stored in django-celery-results table
```

Redis is like a waiting room for jobs.

Celery workers are like employees who take jobs from that waiting room.

## 16. Retry And Failed Task Handling

Each Celery task has retry settings:

```python
autoretry_for=(Exception,)
retry_backoff=True
retry_kwargs={"max_retries": 3}
```

This means:

- if a task fails because of a temporary problem, Celery retries it
- retries wait longer each time
- the task does not retry forever

This is important because background systems must handle failure.

## 17. Resource Management

The project controls resources in several ways.

### DRF Throttling

Configured in:

```text
commerce_engine/settings.py
```

Rates:

```text
anonymous users: 30/min
logged-in users: 120/min
login endpoint: 10/min
checkout endpoint: 20/min
```

This prevents one user from sending too many requests.

### Capacity Middleware

Defined in:

```text
shop/middleware.py
```

It uses a bounded semaphore.

Settings:

```text
MAX_CONCURRENT_REQUESTS = 20
CAPACITY_WAIT_SECONDS = 2
```

This means the server accepts only 20 active requests at the same time.

If it is full, a request waits up to 2 seconds. If there is still no space, the
server returns:

```text
503 Service Unavailable
```

### Celery Worker Limits

Configured in:

```text
commerce_engine/settings.py
```

Important settings:

```text
CELERY_WORKER_CONCURRENCY = 4
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = 30
CELERY_TASK_SOFT_TIME_LIMIT = 20
```

These prevent background workers from taking unlimited work or running forever.

## 18. How To Run The Project

Open PowerShell in:

```text
C:\Users\mhdta\Documents\New project
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Apply migrations:

```powershell
python manage.py migrate
```

Create demo data:

```powershell
python manage.py seed_demo
```

Start Django:

```powershell
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/api/health/
```

Expected:

```json
{"status":"ok"}
```

## 19. How To Run Redis

Redis must be running for Celery queue processing and Redis cache.

Default Redis URLs:

```text
redis://127.0.0.1:6379/0
redis://127.0.0.1:6379/1
```

If Redis is not running, basic API testing may still work, but Celery workers
cannot process queued tasks properly.

The easiest way to run Redis is Docker Compose:

```powershell
docker compose up --build
```

This starts Redis automatically in a container named:

```text
commerce_redis
```

Check Redis:

```powershell
docker compose exec redis redis-cli ping
```

Expected:

```text
PONG
```

For the full Docker setup, read:

```text
DOCKER_GUIDE.md
```

## 20. How To Run Celery Worker

Open a second PowerShell terminal.

Run:

```powershell
celery -A commerce_engine worker -l info --pool=solo -Q emails,invoices,analytics
```

The `--pool=solo` option is useful on Windows because Celery process pools are
more limited on Windows.

When checkout happens, you should see task logs in this terminal.

## 21. Optional Flower Monitoring

Open another terminal:

```powershell
celery -A commerce_engine flower
```

Then open:

```text
http://127.0.0.1:5555
```

Flower lets you see:

- workers
- active tasks
- completed tasks
- failed tasks
- retries

## 22. Demo Users

The seed command creates:

```text
student / student123
admin / admin12345
```

Use `student` for normal checkout.

Use `admin` for admin-only endpoints like stock update and task results.

## 23. How To Test With Postman

### Step 1: Health Check

Method:

```text
GET
```

URL:

```text
http://127.0.0.1:8000/api/health/
```

Expected:

```json
{
  "status": "ok"
}
```

### Step 2: Login

Method:

```text
POST
```

URL:

```text
http://127.0.0.1:8000/api/auth/login/
```

Body:

```json
{
  "username": "student",
  "password": "student123"
}
```

Copy the returned token.

### Step 3: Product List

Method:

```text
GET
```

URL:

```text
http://127.0.0.1:8000/api/products/
```

Expected:

```json
{
  "products": [
    {
      "id": 1,
      "name": "Laptop Stand",
      "description": "Aluminum stand for a desk setup",
      "price": "29.99",
      "stock_quantity": 50,
      "version": 0
    }
  ]
}
```

### Step 4: Checkout

Method:

```text
POST
```

URL:

```text
http://127.0.0.1:8000/api/checkout/
```

Header:

```text
Authorization: Token YOUR_TOKEN_HERE
```

Body:

```json
{
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    }
  ]
}
```

Expected:

```json
{
  "order": {
    "id": 1,
    "customer_email": "student@example.com",
    "status": "paid",
    "total_amount": "59.98"
  },
  "queued_background_tasks": [
    "send_order_confirmation",
    "generate_invoice",
    "log_order_analytics"
  ]
}
```

### Step 5: Check Orders

Method:

```text
GET
```

URL:

```text
http://127.0.0.1:8000/api/orders/
```

Header:

```text
Authorization: Token YOUR_TOKEN_HERE
```

This shows the orders for the logged-in user.

### Step 6: Check Task Results

Login as admin and use the admin token.

Method:

```text
GET
```

URL:

```text
http://127.0.0.1:8000/api/tasks/results/
```

Header:

```text
Authorization: Token ADMIN_TOKEN_HERE
```

This shows recent Celery task results stored by `django-celery-results`.

## 24. How To Test With PowerShell

Health:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health/ |
  Select-Object -ExpandProperty Content
```

Login:

```powershell
$login = @{
  username = "student"
  password = "student123"
} | ConvertTo-Json

$response = Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/api/auth/login/ `
  -Method POST `
  -ContentType "application/json" `
  -Body $login

$token = $response.token
```

Checkout:

```powershell
$body = @{
  items = @(
    @{
      product_id = 1
      quantity = 1
    }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/api/checkout/ `
  -Method POST `
  -ContentType "application/json" `
  -Headers @{ Authorization = "Token $token" } `
  -Body $body
```

## 25. How To Test Race Condition Prevention

Run:

```powershell
python manage.py simulate_concurrent_checkout --buyers 20 --stock 5
```

This means:

- create or use a demo product
- set its stock to 5
- start 20 buyer threads
- each buyer tries to buy 1 item

Expected:

```text
Successful orders: 5
Rejected orders: 15
Final stock: 0
```

This proves that even when 20 buyers try at the same time, only 5 can buy
because only 5 items exist.

## 26. How To View Results

You can view results in several places.

### API responses

Postman or PowerShell show JSON responses immediately.

### Product stock

Call:

```text
GET /api/products/
```

Before checkout, stock may be 50.

After buying 2, stock should be 48.

### Orders

Call:

```text
GET /api/orders/
```

This shows created orders.

### Celery worker terminal

When tasks run, the Celery terminal shows logs.

### Task results API

Call:

```text
GET /api/tasks/results/
```

This shows saved task results from `django-celery-results`.

### Django admin

Create or use the seeded admin user:

```text
admin / admin12345
```

Open:

```text
http://127.0.0.1:8000/admin/
```

You can view:

- users
- products
- orders
- order items
- Celery task results

## 27. How To Explain This In Discussion

A good explanation:

> I built a small Django REST backend for e-commerce checkout. The main shared
> resource is product stock. I used database transactions and select_for_update
> to lock product rows during checkout, so concurrent users cannot buy the same
> last item. I used Celery and Redis to move slow tasks like email, invoice, and
> analytics outside the request-response cycle. I also added throttling,
> capacity middleware, worker limits, retries, and timeouts to show resource
> management.

## 28. What Happens If Redis Is Down

If Redis is down:

- product APIs may still work because cache failures are ignored
- Celery tasks cannot be queued or processed normally
- throttling/cache behavior may be limited depending on configuration

This is useful to mention because Redis is an external dependency.

## 29. What Happens If Stock Is Not Enough

The service raises:

```python
OutOfStockError
```

The API returns:

```text
409 Conflict
```

The transaction rolls back.

No invalid order is created.

## 30. What To Say About SQLite And PostgreSQL

SQLite is simple for local development.

PostgreSQL is better for real concurrency testing because `select_for_update()`
is designed for databases with row-level locking.

So you can say:

> I kept SQLite available so the project is easy to run, but the design is
> PostgreSQL-ready. For the final concurrency demo, PostgreSQL is the correct
> database because it supports row-level locks.

## 31. Important Commands Summary

Install:

```powershell
python -m pip install -r requirements.txt
```

Migrate:

```powershell
python manage.py migrate
```

Seed data:

```powershell
python manage.py seed_demo
```

Run server:

```powershell
python manage.py runserver
```

Run Celery:

```powershell
celery -A commerce_engine worker -l info --pool=solo -Q emails,invoices,analytics
```

Run tests:

```powershell
python manage.py test
```

Run concurrency demo:

```powershell
python manage.py simulate_concurrent_checkout --buyers 20 --stock 5
```

Run system check:

```powershell
python manage.py check
```

## 32. Final Simple Summary

The project works like this:

1. Users log in and get a token.
2. Users view products.
3. Users send checkout requests.
4. The backend locks product stock rows.
5. The backend safely decreases stock.
6. The backend creates an order.
7. The backend queues background jobs.
8. Celery workers process slow tasks separately.
9. Redis helps with queues and caching.
10. Tests and simulation prove the system prevents overselling.

The project is small, but it demonstrates strong backend engineering and real
parallel programming concepts.
