from django.db import transaction

from .models import BackgroundTask


def process_next_task() -> bool:
    with transaction.atomic():
        task = (
            BackgroundTask.objects.select_for_update()
            .filter(status=BackgroundTask.Status.QUEUED)
            .order_by("created_at")
            .first()
        )
        if task is None:
            return False

        task.status = BackgroundTask.Status.RUNNING
        task.attempts += 1
        task.save(update_fields=["status", "attempts", "updated_at"])

    try:
        _handle_task(task)
    except Exception as exc:
        task.status = BackgroundTask.Status.FAILED
        task.last_error = str(exc)
        task.save(update_fields=["status", "last_error", "updated_at"])
        return True

    task.status = BackgroundTask.Status.DONE
    task.last_error = ""
    task.save(update_fields=["status", "last_error", "updated_at"])
    return True


def _handle_task(task: BackgroundTask) -> None:
    if task.kind == BackgroundTask.Kind.EMAIL:
        print(f"Sending order email to {task.payload['email']}")
        return

    if task.kind == BackgroundTask.Kind.INVOICE:
        print(f"Generating invoice for order #{task.payload['order_id']}")
        return

    raise ValueError(f"unsupported task kind: {task.kind}")
