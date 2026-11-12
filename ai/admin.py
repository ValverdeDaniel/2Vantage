from django import forms
from django.contrib import admin

from deals import carriers

from .models import Call, CarrierNote, Chat, DealAi, Job


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


class CarrierNoteForm(forms.ModelForm):
    """The carrier is picked from the carriers' list (deals/carriers.py), never typed (D119)."""

    carrier = forms.ChoiceField(choices=())

    class Meta:
        model = CarrierNote
        fields = ('carrier', 'text')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['carrier'].choices = [(row['key'], row['name']) for row in carriers.CARRIERS]


@admin.register(CarrierNote)
class CarrierNoteAdmin(admin.ModelAdmin):
    """An admin's note per carrier, added to every Claude call about that carrier, outside the cache (D119)."""

    form = CarrierNoteForm
    list_display = ('carrier', 'text', 'updated_by', 'updated_at')

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    """Read-only: chats change only through Work with Claude."""

    list_display = ('id', 'deal', 'number', 'title', 'tab', 'last_used_at', 'last_used_by')
    readonly_fields = [field.name for field in Chat._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
