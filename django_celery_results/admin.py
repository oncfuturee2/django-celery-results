"""Result Task Admin interface."""

import logging

from celery import current_app as celery_app
from django.conf import settings
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from .models import GroupResult, TaskResult

logger = logging.getLogger(__name__)

try:
    ALLOW_EDITS = settings.DJANGO_CELERY_RESULTS['ALLOW_EDITS']
except (AttributeError, KeyError):
    ALLOW_EDITS = False
    pass


class TaskResultAdmin(admin.ModelAdmin):
    """Admin-interface for results of tasks."""

    model = TaskResult
    date_hierarchy = 'date_done'
    list_display = ('task_id', 'periodic_task_name', 'task_name', 'date_done',
                    'status', 'worker', 'duration')
    list_filter = ('status', 'date_done', 'periodic_task_name', 'task_name',
                   'worker')
    readonly_fields = ('date_created', 'date_started', 'date_done',
                       'result', 'meta', 'duration')
    search_fields = ('task_name', 'task_id', 'status', 'task_args',
                     'task_kwargs')
    fieldsets = (
        (None, {
            'fields': (
                'task_id',
                'task_name',
                'periodic_task_name',
                'status',
                'worker',
                'content_type',
                'content_encoding',
            ),
            'classes': ('extrapretty', 'wide')
        }),
        (_('Parameters'), {
            'fields': (
                'task_args',
                'task_kwargs',
            ),
            'classes': ('extrapretty', 'wide')
        }),
        (_('Result'), {
            'fields': (
                'result',
                'date_created',
                'date_started',
                'date_done',
                'traceback',
                'meta',
            ),
            'classes': ('extrapretty', 'wide')
        }),
    )
    actions = ['terminate_task']

    def get_readonly_fields(self, request, obj=None):
        if ALLOW_EDITS:
            return self.readonly_fields
        else:
            return list({
                field.name for field in self.model._meta.fields
            }) + ['duration']

    def get_form(self, request, obj=None, change=False, **kwargs):
        if 'fields' in kwargs:
            kwargs['fields'] = tuple(
                f for f in kwargs['fields'] if f != 'duration'
            )
        return super().get_form(request, obj, change, **kwargs)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        result_fieldset = None
        for name, options in fieldsets:
            if name == _('Result'):
                result_fieldset = (name, dict(options))
                break
        if result_fieldset is not None:
            fields = list(result_fieldset[1]['fields'])
            try:
                idx = fields.index('date_done')
                fields.insert(idx + 1, 'duration')
            except ValueError:
                fields.append('duration')
            result_fieldset[1]['fields'] = tuple(fields)
            fieldsets = tuple(
                (name, result_fieldset[1] if name == _('Result') else options)
                for name, options in fieldsets
            )
        return fieldsets

    @admin.display(description=_('Duration (seconds)'))
    def duration(self, obj):
        return obj.duration

    def terminate_task(self, request, queryset):
        """Terminate selected tasks."""
        task_ids = list(queryset.values_list('task_id', flat=True))
        try:
            celery_app.control.terminate(task_ids)
            self.message_user(
                request,
                f"{len(task_ids)} task(s) was terminated successfully.",
                messages.SUCCESS,
            )
        except Exception as e:
            logger.error(
                "Error while terminating tasks: %s",
                e,
                exc_info=True,
                extra={'task_ids': task_ids}
            )
            self.message_user(
                request,
                f"Error while terminating tasks: {e}",
                messages.ERROR,
            )

    terminate_task.short_description = _("Terminate selected tasks")


admin.site.register(TaskResult, TaskResultAdmin)


class GroupResultAdmin(admin.ModelAdmin):
    """Admin-interface for results  of grouped tasks."""

    model = GroupResult
    date_hierarchy = 'date_done'
    list_display = ('group_id', 'date_done')
    list_filter = ('date_done',)
    readonly_fields = ('date_created', 'date_done', 'result')
    search_fields = ('group_id',)


admin.site.register(GroupResult, GroupResultAdmin)
