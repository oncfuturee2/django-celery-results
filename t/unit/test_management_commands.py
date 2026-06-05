from datetime import timedelta
from io import StringIO

import pytest
from celery import states, uuid
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from django_celery_results.models import GroupResult, TaskResult
from django_celery_results.utils import now


class test_DeleteExpiredResultsCommand(TestCase):
    def create_task_result(self, task_id=None):
        return TaskResult.objects.create(
            task_id=task_id or uuid(),
            status=states.SUCCESS,
            content_type='application/json',
            content_encoding='utf-8',
            result='"ok"',
        )

    def create_group_result(self, group_id=None):
        return GroupResult.objects.create(
            group_id=group_id or uuid(),
            content_type='application/json',
            content_encoding='utf-8',
            result='[]',
        )

    def test_command_deletes_only_expired_task_and_group_results(self):
        expired_task = self.create_task_result()
        fresh_task = self.create_task_result()
        expired_group = self.create_group_result()
        fresh_group = self.create_group_result()

        TaskResult.objects.filter(pk=expired_task.pk).update(
            date_done=now() - timedelta(days=10)
        )
        GroupResult.objects.filter(pk=expired_group.pk).update(
            date_done=now() - timedelta(days=10)
        )

        stdout = StringIO()
        call_command('delete_expired_results', days=7, stdout=stdout)
        output = stdout.getvalue()

        assert not TaskResult.objects.filter(pk=expired_task.pk).exists()
        assert TaskResult.objects.filter(pk=fresh_task.pk).exists()
        assert not GroupResult.objects.filter(pk=expired_group.pk).exists()
        assert GroupResult.objects.filter(pk=fresh_group.pk).exists()
        assert 'TaskResult: deleted 1 expired records from database "default".' in output
        assert 'GroupResult: deleted 1 expired records from database "default".' in output
        assert 'Finished cleaning expired Celery results older than 7 day(s). Total deleted: 2.' in output

    def test_command_rejects_negative_days(self):
        with pytest.raises(CommandError, match='--days must be greater than or equal to 0.'):
            call_command('delete_expired_results', days=-1)
