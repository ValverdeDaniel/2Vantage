"""The firm's pages and team, edited in Django admin until slice 34 (plan.md §6.11; J125, J155; OQ41)."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from proposals.admin import FirmPagesForm, TeamMemberForm
from proposals.models import FirmPages, TeamMember

pytestmark = pytest.mark.django_db


def _photo(size=(1600, 1000)):
    buffer = io.BytesIO()
    exif = Image.Exif()
    exif[0x010F] = 'Zqcamera'  # a maker tag a re-encode must drop
    Image.new('RGB', size, '#336699').save(buffer, format='JPEG', exif=exif)
    return SimpleUploadedFile('me.jpg', buffer.getvalue(), content_type='image/jpeg')


def test_J155_firm_pages_read_blank_without_making_a_row():
    found = FirmPages.get()
    assert (found.about_text, found.about_stats, found.service_calendar) == ('', [], [])
    assert not FirmPages.objects.exists()


def test_J155_firm_pages_keep_their_limits():
    too_many = [{'value': str(n), 'label': 'x'} for n in range(FirmPages.MAX_STATS + 1)]
    form = FirmPagesForm(
        data={
            'about_text': 'a' * (FirmPages.MAX_ABOUT + 1),
            'about_stats': too_many,
            'service_calendar': [{'meeting': 'Kick-off', 'topics': 'not a list'}],
        }
    )
    assert not form.is_valid()
    assert set(form.errors) == {'about_text', 'about_stats', 'service_calendar'}
    good = FirmPagesForm(
        data={
            'about_text': 'Who we are.',
            'about_stats': [{'value': '20+', 'label': 'Years'}],
            'service_calendar': [{'meeting': 'Kick-off', 'topics': ['Goals'], 'when': 'January'}],
        }
    )
    assert good.is_valid(), good.errors
    good.save()
    assert FirmPages.objects.get().pk == 1


def test_J155_a_photo_is_re_encoded_small_with_no_metadata():
    form = TeamMemberForm(
        data={'name': 'Rosa Example', 'sort_order': 0, 'on_by_default': True}, files={'photo': _photo()}
    )
    assert form.is_valid(), form.errors
    member = form.save()
    with member.photo.open('rb') as handle:
        image = Image.open(io.BytesIO(handle.read()))
        assert image.format == 'JPEG'
        assert max(image.size) <= 800
        assert 'Zqcamera' not in str(dict(image.getexif()))


def test_J155_a_bio_and_the_team_keep_their_limits():
    form = TeamMemberForm(data={'name': 'Long', 'bio': 'b' * (TeamMember.MAX_BIO + 1), 'sort_order': 0})
    assert not form.is_valid() and 'bio' in form.errors
    TeamMember.objects.bulk_create(TeamMember(name=f'P{n}') for n in range(TeamMember.MAX_MEMBERS))
    full = TeamMemberForm(data={'name': 'One more', 'sort_order': 0})
    assert not full.is_valid()
