"""Django admin: agency settings and a read-only look at clients (plan.md §7.2, §8.14)."""

import io

from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image

from .models import AgencySettings, Client

MAX_LOGO_BYTES = 2 * 1024 * 1024


class AgencySettingsForm(forms.ModelForm):
    class Meta:
        model = AgencySettings
        fields = [
            'name',
            'address',
            'city_state_zip',
            'phone',
            'email',
            'brand_color',
            'logo',
            'default_commission',
            'rfp_return_email',
        ]

    def clean_logo(self):
        upload = self.cleaned_data.get('logo')
        if not upload or not hasattr(upload, 'content_type'):
            return upload
        if upload.size > MAX_LOGO_BYTES:
            raise ValidationError('The logo can be up to 2 MB.')
        try:
            image = Image.open(upload)
            image.load()
        except Exception as exc:
            raise ValidationError('The logo must be a PNG or JPEG image.') from exc
        # Re-encode as PNG: drops metadata and anything that is not pixels.
        clean = Image.new('RGBA', image.size)
        clean.paste(image.convert('RGBA'))
        buffer = io.BytesIO()
        clean.save(buffer, format='PNG')
        return ContentFile(buffer.getvalue(), name='logo.png')

    def clean_brand_color(self):
        color = self.cleaned_data['brand_color']
        if not (len(color) == 7 and color.startswith('#')):
            raise ValidationError('Use #rrggbb.')
        return color


@admin.register(AgencySettings)
class AgencySettingsAdmin(admin.ModelAdmin):
    form = AgencySettingsForm

    def has_add_permission(self, request):
        return not AgencySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'relationship', 'owner', 'created_at')
    search_fields = ('name',)


User = get_user_model()
admin.site.unregister(User)


@admin.register(User)
class SafeUserAdmin(UserAdmin):
    """An admin cannot deactivate or demote themselves (§8.14)."""

    def save_model(self, request, obj, form, change):
        if change and obj.pk == request.user.pk and (not obj.is_active or not obj.is_staff):
            messages.error(request, "Not saved: you can't remove your own admin access or deactivate yourself.")
            return
        super().save_model(request, obj, form, change)
