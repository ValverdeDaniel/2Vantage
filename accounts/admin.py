"""Users and their Profile flags in Django admin (plan.md §6.1, §7.2, §8.14; A3)."""

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Flags'
    fields = ('claude_direct', 'commissions_access')


User = get_user_model()
admin.site.unregister(User)


@admin.register(User)
class SafeUserAdmin(UserAdmin):
    """An admin cannot deactivate or demote themselves (§8.14). The flags sit inline (A3)."""

    inlines = [ProfileInline]

    def _refused(self, request, obj, change):
        return change and obj.pk == request.user.pk and (not obj.is_active or not obj.is_staff)

    def save_model(self, request, obj, form, change):
        if self._refused(request, obj, change):
            messages.error(request, "Not saved: you can't remove your own admin access or deactivate yourself.")
            return
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        if not self._refused(request, form.instance, change):
            super().save_related(request, form, formsets, change)
