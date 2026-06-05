import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from django_celery_results.models import GroupResult, TaskResult

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clean up expired Celery task results from the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "days",
            type=int,
            help="Number of days to retain task results. Results older than this will be deleted.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100000,
            help="Number of records to delete per batch (default: 100000).",
        )

    def _delete_expired_and_count(self, model, expires, batch_size):
        total_deleted = 0
        qs = model.objects.get_all_expired(expires).order_by("id")

        while True:
            ids = list(qs.values_list("id", flat=True)[:batch_size])
            if not ids:
                break
            count = len(ids)
            total_deleted += count
            with transaction.atomic():
                model.objects.filter(id__in=ids).delete()

        return total_deleted

    def handle(self, *args, **options):
        days = options["days"]
        batch_size = options["batch_size"]

        self.stdout.write(
            self.style.WARNING(
                f"Starting cleanup of task results older than {days} days..."
            )
        )

        task_result_count = self._delete_expired_and_count(
            TaskResult, days, batch_size
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {task_result_count} expired TaskResult records."
            )
        )

        group_result_count = self._delete_expired_and_count(
            GroupResult, days, batch_size
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {group_result_count} expired GroupResult records."
            )
        )

        total_deleted = task_result_count + group_result_count
        self.stdout.write(
            self.style.SUCCESS(
                f"Cleanup complete. Total records deleted: {total_deleted}"
            )
        )
