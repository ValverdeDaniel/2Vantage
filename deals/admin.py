"""Django admin: agency settings and a read-only look at clients (plan.md §7.2, §8.14). Users: accounts/admin.py."""

import io

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image

from .models import Activity, AgencySettings, Client

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
            'producer_name',
            'producer_npn',
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
    list_display = ('name', 'relationship', 'client_since', 'owner', 'created_at')
    list_filter = ('relationship',)
    search_fields = ('name',)
    # The status changes only through deals.services.set_status and sale_changed (§5.1), never here.
    readonly_fields = ('relationship', 'client_since', 'converted_by_sale')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    """Read-only: the log, including the downloads and views the deal feed leaves out (§3.8)."""

    list_display = ('updated_at', 'deal', 'area', 'action', 'actor', 'actor_kind', 'summary', 'count', 'document_id')
    list_filter = ('area', 'action', 'actor_kind')
    list_select_related = ('deal__client', 'actor')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

