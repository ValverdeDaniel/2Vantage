from django.contrib import admin

from .models import Call, DealAi, Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """Read-only: jobs change only through the worker and the ai services."""

    list_display = ('id', 'deal', 'kind', 'lane', 'status', 'progress', 'created_by', 'created_at', 'finished_at')
    list_filter = ('kind', 'lane', 'status')
    readonly_fields = [field.name for field in Job._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DealAi)
class DealAiAdmin(admin.ModelAdmin):
    list_display = ('deal', 'locked_by', 'locked_at', 'budget_usd')
    readonly_fields = ('deal', 'next_chat')


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    """The ledger of Claude calls, read-only: what each cost. `manage.py ai_spend` adds them up against the cap."""

    list_display = ('id', 'created_at', 'purpose', 'model', 'answered', 'status', 'estimate_usd', 'cost_usd', 'job')
    list_filter = ('purpose', 'status', 'model')
    readonly_fields = [field.name for field in Call._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
