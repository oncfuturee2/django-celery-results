from celery.utils.time import maybe_timedelta
from django.core.management.base import BaseCommand

from django_celery_results.models import TaskResult, GroupResult


class Command(BaseCommand):
    help = 'Clean up expired Celery task and group results from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to keep task results (default: 30)',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=None,
            help='Number of hours to keep task results (alternative to --days)',
        )
        parser.add_argument(
            '--minutes',
            type=int,
            default=None,
            help='Number of minutes to keep task results (alternative to --days)',
        )

    def handle(self, *args, **options):
        if options['minutes'] is not None:
            expires = options['minutes'] * 60
        elif options['hours'] is not None:
            expires = options['hours'] * 3600
        else:
            expires = options['days'] * 86400

        self.stdout.write(f'Starting cleanup of expired results...')
        self.stdout.write(f'Keeping results from last {expires} seconds ({expires / 86400:.2f} days)')

        task_count_before = TaskResult.objects.count()
        group_count_before = GroupResult.objects.count()

        TaskResult.objects.delete_expired(expires)
        GroupResult.objects.delete_expired(expires)

        task_count_after = TaskResult.objects.count()
        group_count_after = GroupResult.objects.count()

        tasks_deleted = task_count_before - task_count_after
        groups_deleted = group_count_before - group_count_after

        self.stdout.write(self.style.SUCCESS('Cleanup completed!'))
        self.stdout.write(f'  Task results deleted: {tasks_deleted}')
        self.stdout.write(f'  Group results deleted: {groups_deleted}')
        self.stdout.write(f'  Total records deleted: {tasks_deleted + groups_deleted}')
