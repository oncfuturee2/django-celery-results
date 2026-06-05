from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError

from django_celery_results.models import GroupResult, TaskResult


class Command(BaseCommand):
    help = 'Delete expired Celery task and group results from the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            required=True,
            help='Keep records completed within the last N days.',
        )
        parser.add_argument(
            '--database',
            default='default',
            help='Nominates a database to clean. Defaults to "default".',
        )

    def handle(self, *args, **options):
        days = options['days']
        database = options['database']

        if days < 0:
            raise CommandError('--days must be greater than or equal to 0.')

        expires = timedelta(days=days)
        task_manager = TaskResult.objects.db_manager(database)
        group_manager = GroupResult.objects.db_manager(database)

        expired_task_count = task_manager.get_all_expired(expires).count()
        expired_group_count = group_manager.get_all_expired(expires).count()

        task_manager.delete_expired(expires)
        group_manager.delete_expired(expires)

        total_deleted = expired_task_count + expired_group_count

        self.stdout.write(
            f'TaskResult: deleted {expired_task_count} expired records '
            f'from database "{database}".'
        )
        self.stdout.write(
            f'GroupResult: deleted {expired_group_count} expired records '
            f'from database "{database}".'
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Finished cleaning expired Celery results older than '
                f'{days} day(s). Total deleted: {total_deleted}.'
            )
        )
