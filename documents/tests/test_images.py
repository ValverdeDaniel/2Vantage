"""The images helper (plan.md §3.8, §6.11; J33, J155, ch25): only PNG and JPEG, within caps; what is stored is a fresh
JPEG with no metadata, upright, on white; a fitted crop is cached and a broken file gives None."""

import io

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import FieldFile
from PIL import Image

from documents import images

MAKER = 'Zqcamera-images'


def _bytes(size=(400, 300), fmt='JPEG', mode='RGB', colour='#336699', exif=False, **options):
    buffer = io.BytesIO()
    if exif:
        tags = Image.Exif()
        tags[0x010F] = MAKER
        tags[0x0112] = 6  # "turn me 90°": the re-encode must turn the pixels and drop the tag
        options['exif'] = tags
    Image.new(mode, size, colour).save(buffer, format=fmt, **options)
    return buffer.getvalue()


def _upload(name, data):
    return SimpleUploadedFile(name, data)


def _check(name, data, max_bytes=1024 * 1024, max_side=2000):
    return images.checked(_upload(name, data), max_bytes=max_bytes, max_side=max_side, noun='cover image')


@pytest.mark.parametrize(
    ('name', 'data'),
    [
        ('logo.svg', b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'),
        ('cover.gif', _bytes(fmt='GIF', mode='P')),
        ('cover.webp', _bytes(fmt='WEBP')),
        ('notes.txt', b'just text'),
    ],
)
def test_J33_only_png_and_jpeg_are_taken(name, data):
    with pytest.raises(images.Refused) as refused:
        _check(name, data)
    assert 'PNG or JPEG' in str(refused.value)
    assert name not in str(refused.value)


def test_J33_a_renamed_file_is_refused_by_what_it_is_not_its_name():
    with pytest.raises(images.Refused, match='PNG or JPEG'):
        _check('cover.jpg', _bytes(fmt='GIF', mode='P'))
    with pytest.raises(images.Refused, match='not a readable'):
        _check('cover.png', b'%PDF-1.7 not a picture')


def test_J33_the_byte_and_pixel_caps_hold():
    data = _bytes(size=(2400, 100))
    with pytest.raises(images.Refused, match='larger than 2000 pixels'):
        _check('wide.jpg', data)
    with pytest.raises(images.Refused, match='larger than 1 MB'):
        _check('big.png', b'\x89PNG\r\n\x1a\n' + b'0' * (1024 * 1024 + 1))
    assert _check('fine.png', _bytes(fmt='PNG')).startswith(b'\x89PNG')


def test_J33_J155_the_stored_picture_is_a_fresh_jpeg_upright_with_no_metadata():
    data = _check('phone.jpg', _bytes(size=(1600, 1000), exif=True))
    stored, size = images.reencode(data, 800)
    assert stored.startswith(b'\xff\xd8\xff')
    assert MAKER.encode() not in stored and b'Exif' not in stored
    with Image.open(io.BytesIO(stored)) as found:
        assert found.size == size == (500, 800)  # turned upright (orientation 6), then the long side brought to 800
        assert not found.getexif()


def test_J33_transparency_is_laid_on_white():
    data = _bytes(size=(20, 20), fmt='PNG', mode='RGBA', colour=(0, 0, 0, 0))
    stored, _size = images.reencode(data, 100)
    with Image.open(io.BytesIO(stored)) as found:
        assert all(channel > 245 for channel in found.convert('RGB').getpixel((10, 10)))


def test_J35_fit_crops_to_the_box_and_never_blows_a_small_picture_up():
    wide = images.fit(_bytes(size=(1000, 500)), (300, 300))
    with Image.open(io.BytesIO(wide)) as found:
        assert found.size == (300, 300)
    small = images.fit(_bytes(size=(100, 50)), (300, 300))
    with Image.open(io.BytesIO(small)) as found:
        assert found.size == (50, 50)


def test_J35_fitted_reads_a_stored_file_once_and_a_missing_one_gives_none(tmp_path):
    storage = FileSystemStorage(location=str(tmp_path))
    name = storage.save('cover.jpg', ContentFile(_bytes(size=(600, 400), colour='#aa0000')))
    field = FieldFile(None, type('F', (), {'storage': storage})(), name)
    first = images.fitted(field, (120, 120))
    storage.delete(name)
    assert images.fitted(field, (120, 120)) is None  # gone from storage: no picture, no error
    storage.save('cover.jpg', ContentFile(_bytes(size=(600, 400), colour='#aa0000')))
    again = FieldFile(None, type('F', (), {'storage': storage})(), name)
    assert images.fitted(again, (120, 120)) == first
