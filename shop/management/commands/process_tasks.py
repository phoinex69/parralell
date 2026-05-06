import time

from django.core.management.base import BaseCommand

from shop.tasks import process_next_task


class Command(BaseCommand):
    help = "Processes queued background tasks outside the HTTP request flow."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process one batch and stop.")
        parser.add_argument("--sleep", type=float, default=1.0, help="Seconds between polls.")

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Background worker started"))

        while True:
            processed = process_next_task()
            if options["once"] and not processed:
                self.stdout.write("No queued tasks found")
                return

            if options["once"]:
                self.stdout.write("Processed one task")
                return

            if not processed:
                time.sleep(options["sleep"])
