import datetime
import json
from types import SimpleNamespace

import pytest
from celery import states, uuid

from django_celery_results.backends.database import DatabaseBackend
from django_celery_results.models import TaskResult


@pytest.mark.django_db()
@pytest.mark.usefixtures('depends_on_current_app')
class test_DatabaseBackendStoreResult:

    @pytest.fixture(autouse=True)
    def setup_backend(self):
        self.app.conf.result_serializer = 'json'
        self.app.conf.result_backend = (
            'django_celery_results.backends:DatabaseBackend')
        self.app.conf.result_extended = True
        self.backend = DatabaseBackend(app=self.app)

    def _create_request(self, name, args, kwargs,
                        argsrepr=None, kwargsrepr=None, task_protocol=2):
        request = SimpleNamespace(
            task=name,
            args=args,
            kwargs=kwargs,
            argsrepr=argsrepr if task_protocol == 2 else None,
            kwargsrepr=kwargsrepr if task_protocol == 2 else None,
            children=[],
            meta={},
            hostname=None,
            periodic_task_name=None,
        )
        return request

    def test_store_result_persists_regular_state_request_meta(self):
        task_id = uuid()
        request = self._create_request(
            name='regular_task',
            args=['alpha', 2],
            kwargs={'flag': True},
            task_protocol=1,
        )
        request.hostname = 'celery@regular'
        request.meta = {'request_id': 'req-1', 'retries': 1}

        self.backend._store_result(
            task_id=task_id,
            result={'ok': True},
            status=states.SUCCESS,
            request=request,
        )

        task_result = TaskResult.objects.get(task_id=task_id)
        decoded_meta = self.backend.get_task_meta(task_id)

        assert task_result.status == states.SUCCESS
        assert task_result.date_started is None
        assert task_result.task_name == 'regular_task'
        assert task_result.periodic_task_name is None
        assert task_result.worker == 'celery@regular'
        assert json.loads(task_result.result) == {'ok': True}
        assert json.loads(task_result.meta) == {
            'request_id': 'req-1',
            'retries': 1,
            'children': [],
        }
        assert json.loads(task_result.task_args) == ['alpha', 2]
        assert json.loads(task_result.task_kwargs) == {'flag': True}
        assert decoded_meta['request_id'] == 'req-1'
        assert decoded_meta['children'] == []
        assert decoded_meta['task_args'] == ['alpha', 2]
        assert decoded_meta['task_kwargs'] == {'flag': True}

    def test_store_result_sets_date_started_for_started_state(self):
        task_id = uuid()
        request = self._create_request(
            name='started_task',
            args=[],
            kwargs={},
            task_protocol=1,
        )
        request.meta = {'phase': 'starting'}

        self.backend._store_result(
            task_id=task_id,
            result=None,
            status=states.STARTED,
            request=request,
        )

        task_result = TaskResult.objects.get(task_id=task_id)
        decoded_meta = self.backend.get_task_meta(task_id)

        assert task_result.status == states.STARTED
        assert isinstance(task_result.date_started, datetime.datetime)
        assert json.loads(task_result.result) is None
        assert json.loads(task_result.meta) == {
            'phase': 'starting',
            'children': [],
        }
        assert decoded_meta['status'] == states.STARTED
        assert decoded_meta['phase'] == 'starting'
        assert decoded_meta['children'] == []

    def test_store_result_persists_extended_request_properties(self):
        task_id = uuid()
        request = self._create_request(
            name='extended_task',
            args=['secret', 1],
            kwargs={'flag': False},
            argsrepr='masked-args',
            kwargsrepr='masked-kwargs',
        )
        request.hostname = 'celery@extended'
        request.periodic_task_name = 'nightly-sync'
        request.meta = {'origin': 'beat'}
        traceback = 'traceback text'

        self.backend._store_result(
            task_id=task_id,
            result='done',
            status=states.SUCCESS,
            traceback=traceback,
            request=request,
        )

        task_result = TaskResult.objects.get(task_id=task_id)
        decoded_meta = self.backend.get_task_meta(task_id)

        assert task_result.task_name == 'extended_task'
        assert task_result.periodic_task_name == 'nightly-sync'
        assert task_result.worker == 'celery@extended'
        assert task_result.traceback == traceback
        assert json.loads(task_result.task_args) == 'masked-args'
        assert json.loads(task_result.task_kwargs) == 'masked-kwargs'
        assert json.loads(task_result.meta) == {'origin': 'beat', 'children': []}
        assert decoded_meta['task_name'] == 'extended_task'
        assert decoded_meta['worker'] == 'celery@extended'
        assert decoded_meta['task_args'] == 'masked-args'
        assert decoded_meta['task_kwargs'] == 'masked-kwargs'
