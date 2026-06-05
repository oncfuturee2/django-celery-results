from datetime import timedelta
from django.core.management.base import BaseCommand
from django_celery_results.models import TaskResult, GroupResult

class Command(BaseCommand):
    help = 'Clean up expired Celery task results and group results from the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Retain results for this many days. Older results will be deleted (default: 30).'
        )

    def handle(self, *args, **options):
        days = options['days']
        expires = timedelta(days=days)
        
        self.stdout.write(f"Cleaning up Celery results older than {days} days...")
        
        task_count = TaskResult.objects.get_all_expired(expires).count()
        group_count = GroupResult.objects.get_all_expired(expires).count()
        
        TaskResult.objects.delete_expired(expires)
        GroupResult.objects.delete_expired(expires)
        
        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {task_count} expired TaskResults."))
        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {group_count} expired GroupResults."))
