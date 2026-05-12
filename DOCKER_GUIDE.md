# Docker Guide

# Running The E-Commerce Backend With Redis

This guide explains how to run the project with Docker. This is the easiest way
to make Redis work because Docker starts Redis in its own container.

## 1. Why Docker Is Useful Here

The project needs several services:

- Django backend
- Celery worker
- Redis
- PostgreSQL
- optional Flower monitoring

Without Docker, you must install and configure Redis and PostgreSQL directly on
your computer. On Windows, Redis can be annoying to run locally.

With Docker, each service runs inside a container:

```text
web container       -> Django + Gunicorn
worker container    -> Celery worker
redis container     -> Redis queue/cache
db container        -> PostgreSQL database
flower container    -> optional Celery dashboard
```

All containers can talk to each other using service names.

For example, Django connects to Redis using:

```text
redis://redis:6379/0
```

The first `redis` is the Docker Compose service name.

## 2. Files Added For Docker

### Dockerfile

This file describes how to build the Django application image.

It:

1. Uses Python 3.12.
2. Creates `/app` as the working directory.
3. Installs `requirements.txt`.
4. Copies the project code.
5. Exposes port 8000.
6. Starts Gunicorn by default.

### docker-compose.yml

This file starts all services together.

Services:

```text
web
worker
flower
redis
db
```

### .dockerignore

This prevents Docker from copying unnecessary files into the image, such as:

- `.git`
- virtual environments
- Python cache files
- SQLite database
- log files

## 3. First Run

Open PowerShell in the project folder:

```powershell
cd "C:\Users\mhdta\Documents\New project"
```

Build and start the main services:

```powershell
docker compose up --build
```

This starts:

- Django web server
- Celery worker
- Redis
- PostgreSQL

The web container automatically runs:

```text
python manage.py migrate
python manage.py seed_demo
gunicorn ...
```

So the database tables and demo data are created automatically.

## 4. Open The Backend

When the containers are running, open:

```text
http://127.0.0.1:8000/api/health/
```

Expected result:

```json
{"status":"ok"}
```

Product list:

```text
http://127.0.0.1:8000/api/products/
```

## 5. Check That Redis Is Working

In another PowerShell terminal:

```powershell
docker compose exec redis redis-cli ping
```

Expected:

```text
PONG
```

This proves Redis is running.

## 6. Check That PostgreSQL Is Working

Run:

```powershell
docker compose exec db pg_isready -U commerce_user -d commerce_engine
```

Expected:

```text
commerce_engine: accepting connections
```

## 7. View Container Logs

All logs:

```powershell
docker compose logs
```

Django logs only:

```powershell
docker compose logs web
```

Celery logs only:

```powershell
docker compose logs worker
```

Redis logs only:

```powershell
docker compose logs redis
```

## 8. Login And Checkout With Docker

The seeded users are:

```text
student / student123
admin / admin12345
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

After checkout, watch Celery:

```powershell
docker compose logs worker
```

You should see logs for:

```text
send_order_confirmation
generate_invoice
log_order_analytics
```

## 9. Run The Concurrency Demo In Docker

Run:

```powershell
docker compose exec web python manage.py simulate_concurrent_checkout --buyers 20 --stock 5
```

Expected idea:

```text
Successful orders: 5
Rejected orders: 15
Final stock: 0
```

This is the best demonstration for the Parallel Programming course.

## 10. Run Tests In Docker

Run:

```powershell
docker compose exec web python manage.py test
```

Run system check:

```powershell
docker compose exec web python manage.py check
```

## 11. Run Flower Monitoring

Flower is optional. Start it with:

```powershell
docker compose --profile monitoring up flower
```

Open:

```text
http://127.0.0.1:5555
```

Flower shows:

- active Celery workers
- tasks
- retries
- failures
- queues

## 12. Stop Everything

Stop containers:

```powershell
docker compose down
```

Stop containers and delete database/Redis volumes:

```powershell
docker compose down -v
```

Use `-v` only when you want a fresh database.

## 13. How Docker Services Communicate

Inside Docker Compose, containers use service names.

The Django container does not connect to:

```text
127.0.0.1:6379
```

because inside a container, `127.0.0.1` means the container itself.

Instead, it connects to:

```text
redis:6379
```

This works because the Redis service is named `redis` in `docker-compose.yml`.

The PostgreSQL database works the same way:

```text
db:5432
```

## 14. Simple Explanation For Discussion

You can say:

> I dockerized the project because Redis and PostgreSQL are external services.
> Docker Compose lets me run the backend, Redis, PostgreSQL, Celery worker, and
> Flower together with one command. Django connects to Redis using the service
> name `redis`, and Celery uses Redis as the queue broker. This makes the project
> easier to run and easier to demonstrate.

## 15. Common Problems

### Docker Desktop is not running

Start Docker Desktop first, then run:

```powershell
docker compose up --build
```

### Port 8000 is already used

Stop the other server, or change this in `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"
```

Then open:

```text
http://127.0.0.1:8001
```

### Redis check fails

Run:

```powershell
docker compose ps
docker compose logs redis
```

### Database needs reset

Run:

```powershell
docker compose down -v
docker compose up --build
```

This deletes old PostgreSQL and Redis data and starts fresh.
