"""Synthetic pictures, cover uploads and team members for the slice 34 tests (not a test file). Every picture is made
here with Pillow: a flat colour, sometimes with a camera's EXIF a re-encode must drop."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from proposals import cover_services, firm_services

MAKER = 'Zqcamera-s34'  # a maker tag no stored picture may keep


def picture_bytes(size=(1200, 800), fmt='JPEG', colour='#336699', exif=True, mode='RGB'):
    buffer = io.BytesIO()
    image = Image.new(mode, size, colour)
    options = {}
    if exif and fmt == 'JPEG':
        tags = Image.Exif()
        tags[0x010F] = MAKER
        options['exif'] = tags
    image.save(buffer, format=fmt, **options)
    return buffer.getvalue()


def upload(name='cover.jpg', data=None, **picture):
    data = picture_bytes(**picture) if data is None else data
    return SimpleUploadedFile(name, data, content_type='image/jpeg')


def cover(user, label='Harbour at dawn', **picture):
    return cover_services.upload_cover(user, upload(**picture), label)


def person(user, name='Sam Rivera (synthetic)', photo=True, **fields):
    member = firm_services.add_person(user, {'name': name, 'title': 'Benefits advisor', **fields})
    if photo:
        member = firm_services.set_photo(user, member.id, upload('me.jpg', size=(900, 1200), colour='#aa5533'))
    return member
