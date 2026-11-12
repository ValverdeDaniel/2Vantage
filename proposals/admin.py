"""Django admin: the firm's pages and team (plan.md §6.11; J125, J155), edited here until the Firm pages drawer
(slice 34). The forms hold the limits (§6.11): About ≤900 characters, ≤6 figures, ≤8 calendar rows, ≤40 people, a
bio ≤1,400 characters; a photo is re-encoded as a JPEG with no metadata, its long side at most PHOTO_SIDE pixels."""

import io

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

from .models import FirmPages, TeamMember

MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_SIDE = 800
STAT_KEYS = ('value', 'label', 'note')
CALENDAR_KEYS = ('meeting', 'topics', 'when')


def _rows(value, limit, keys, what):
    if value in (None, ''):
        return []
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValidationError(f'Give a list of {what}, each {{{", ".join(keys)}}}.')
    if len(value) > limit:
        raise ValidationError(f'At most {limit} {what}.')
    for row in value:
        unknown = set(row) - set(keys)
        if unknown:
            raise ValidationError(f'Unknown key in {what}: {", ".join(sorted(unknown))}.')
    return value


class FirmPagesForm(forms.ModelForm):
    class Meta:
        model = FirmPages
        fields = ['about_text', 'about_stats', 'service_calendar']

    def clean_about_text(self):
        text = (self.cleaned_data.get('about_text') or '').strip()
        if len(text) > FirmPages.MAX_ABOUT:
            raise ValidationError(f'About the firm can be up to {FirmPages.MAX_ABOUT} characters.')
        return text

    def clean_about_stats(self):
        return _rows(self.cleaned_data.get('about_stats'), FirmPages.MAX_STATS, STAT_KEYS, 'figures')

    def clean_service_calendar(self):
        rows = _rows(self.cleaned_data.get('service_calendar'), FirmPages.MAX_CALENDAR, CALENDAR_KEYS, 'meetings')
        for row in rows:
            if not isinstance(row.get('topics', []), list):
                raise ValidationError("A meeting's topics are a list of words.")
        return rows


@admin.register(FirmPages)
class FirmPagesAdmin(admin.ModelAdmin):
    form = FirmPagesForm

    def has_add_permission(self, request):
        return not FirmPages.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


def reencoded_photo(upload):
    """A person's photo as a fresh JPEG: turned upright, no metadata, its long side at most PHOTO_SIDE."""
    if upload.size > MAX_PHOTO_BYTES:
        raise ValidationError('A photo can be up to 5 MB.')
    try:
        image = Image.open(upload)
        image.load()
    except Exception as exc:
        raise ValidationError('The photo must be a PNG or JPEG image.') from exc
    picture = ImageOps.exif_transpose(image).convert('RGB')
    picture.thumbnail((PHOTO_SIDE, PHOTO_SIDE))
    picture.info = {}
    buffer = io.BytesIO()
    picture.save(buffer, format='JPEG', quality=88)
    return ContentFile(buffer.getvalue(), name='photo.jpg')


class TeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ['name', 'title', 'group', 'phone', 'email', 'bio', 'photo', 'on_by_default', 'sort_order']

    def clean_bio(self):
        bio = (self.cleaned_data.get('bio') or '').strip()
        if len(bio) > TeamMember.MAX_BIO:
            raise ValidationError(f'A bio can be up to {TeamMember.MAX_BIO} characters.')
        return bio

    def clean_photo(self):
        upload = self.cleaned_data.get('photo')
        if not upload or not hasattr(upload, 'content_type'):
            return upload
        return reencoded_photo(upload)

    def clean(self):
        data = super().clean()
        if self.instance.pk is None and TeamMember.objects.count() >= TeamMember.MAX_MEMBERS:
            raise ValidationError(f'The team holds at most {TeamMember.MAX_MEMBERS} people.')
        return data


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    form = TeamMemberForm
    list_display = ('name', 'title', 'group', 'on_by_default', 'sort_order')
    list_editable = ('on_by_default', 'sort_order')
