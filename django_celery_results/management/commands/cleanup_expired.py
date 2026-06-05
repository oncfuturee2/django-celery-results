from datetime import timedelta

from django.core.management.base import BaseCommand

from django_celery_results.models import GroupResult, TaskResult


class Command(BaseCommand):
    help = 'Clean up expired Celery task and group results from the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to retain results. Results completed '
                 'more than this many days ago will be deleted. '
                 '(default: 7)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100000,
            help='Number of records to delete per batch. (default: 100000)',
        )

    def handle(self, *args, **options):
        days = options['days']
        batch_size = options['batch_size']
        expires = timedelta(days=days)

        self.stdout.write(
            self.style.NOTICE(
                f'Cleaning up results older than {days} day(s)...'
            )
        )

        task_count_before = TaskResult.objects.count()
        task_expired_count = TaskResult.objects.get_all_expired(expires).count()
        TaskResult.objects.delete_expired(expires, batch_size=batch_size)

        self.stdout.write(
            self.style.SUCCESS(
                f'TaskResult: {task_expired_count} expired record(s) deleted '
                f'(before: {task_count_before}, after: '
                f'{TaskResult.objects.count()}).'
            )
        )

        group_count_before = GroupResult.objects.count()
        group_expired_count = GroupResult.objects.get_all_expired(
            expires
        ).count()
        GroupResult.objects.delete_expired(expires, batch_size=batch_size)

        self.stdout.write(
            self.style.SUCCESS(
                f'GroupResult: {group_expired_count} expired record(s) deleted '
                f'(before: {group_count_before}, after: '
                f'{GroupResult.objects.count()}).'
            )
        )

        total_deleted = task_expired_count + group_expired_count
        self.stdout.write(
            self.style.SUCCESS(
                f'Cleanup completed. {total_deleted} record(s) deleted '
                f'in total.'
            )
        )