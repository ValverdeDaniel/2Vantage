"""The firm's cover images and the Cover card's tiles (plan.md §6.11, §7.12 `proposal/cover-images/`,
`proposal/covers/`; J32, J33, J35): an upload is checked, re-encoded without metadata, thumbnailed and named
blandly; at most 24; deleting one takes its files; the tiles are one PDF, a page a tile, behind an ETag."""

import io

import pytest
from PIL import Image
from pypdf import PdfReader

from deals import activity
from deals.models import Activity
from proposals import cover_services
from proposals.models import CoverImage
from proposals.tests import firm_shop

pytestmark = pytest.mark.django_db


def _wears(page, colour, slack=12):
    """Whether a page draws a picture of one flat colour (the synthetic uploads are flat)."""
    for image in page.images:
        picture = image.image.convert('RGB')
        middle = picture.getpixel((picture.width // 2, picture.height // 2))
        if all(abs(a - b) <= slack for a, b in zip(middle, colour, strict=True)):
            return True
    return False


def _upload(api, name='Harbour at dawn.jpg', label='Harbour', **picture):
    return api.post('/api/proposal/cover-images/', {'image': firm_shop.upload(name, **picture), 'label': label})


def test_J33_an_upload_is_stored_as_a_fresh_jpeg_with_a_thumbnail(api):
    made = _upload(api, size=(3000, 2000))
    assert made.status_code == 201
    found = made.json()
    assert found['key'] == f'upload:{found["id"]}' and found['label'] == 'Harbour'
    assert (found['width'], found['height']) == (2400, 1600)
    image = CoverImage.objects.get(pk=found['id'])
    assert 'Harbour' not in image.image.name and image.image.name.startswith('proposals/covers/cover')
    with image.image.open('rb') as handle:
        stored = handle.read()
    assert firm_shop.MAKER.encode() not in stored and stored.startswith(b'\xff\xd8\xff')
    thumb = api.get(f'/api/proposal/cover-images/{found["id"]}/thumb/')
    assert thumb['Content-Type'] == 'image/jpeg'
    with Image.open(io.BytesIO(thumb.content)) as picture:
        assert max(picture.size) == CoverImage.THUMB_SIDE
    assert [row['id'] for row in api.get('/api/proposal/cover-images/').json()] == [found['id']]
    row = Activity.objects.get(subject=f'cover_image:{found["id"]}')
    assert row.deal_id is None and row.changes == [{'t': f'cover_image:{found["id"]}', 'k': ['image']}]


def test_J33_a_refused_upload_answers_its_sentence_and_stores_nothing(api):
    svg = api.post('/api/proposal/cover-images/', {'image': firm_shop.upload('cover.svg', b'<svg/>')})
    assert svg.status_code == 400 and svg.json() == {'image': 'A cover image must be a PNG or JPEG file.'}
    assert api.post('/api/proposal/cover-images/', {'label': 'nothing'}).status_code == 400
    assert not CoverImage.objects.exists()


def test_J33_the_firm_holds_at_most_twenty_four_covers(user):
    for _ in range(CoverImage.MAX_IMAGES):
        firm_shop.cover(user, size=(40, 30))
    with pytest.raises(activity.Refused, match='24 cover images'):
        firm_shop.cover(user, size=(40, 30))


def test_J33_deleting_an_upload_takes_its_files_on_commit(api, user, django_capture_on_commit_callbacks):
    image = firm_shop.cover(user)
    storage, names = image.image.storage, (image.image.name, image.thumb.name)
    with django_capture_on_commit_callbacks(execute=True):
        assert api.delete(f'/api/proposal/cover-images/{image.id}/').status_code == 204
    assert not CoverImage.objects.exists()
    assert not any(storage.exists(name) for name in names)
    assert api.delete(f'/api/proposal/cover-images/{image.id}/').status_code == 404


def test_J32_the_tiles_are_one_pdf_a_page_a_tile_behind_an_etag(api, user):
    firm_shop.cover(user, label='First')
    firm_shop.cover(user, label='', colour='#118844')
    response = api.get('/api/proposal/covers/', {'picture': 'none'})
    assert response.status_code == 200 and response['Content-Type'] == 'application/pdf'
    reader = PdfReader(io.BytesIO(response.content))
    texts = [page.extract_text() for page in reader.pages]
    assert len(texts) == 3  # Vantage, then each upload in the firm's order
    assert 'Cover: Vantage' in texts[0] and 'Cover: First' in texts[1] and 'Cover: Your image 2' in texts[2]
    assert not _wears(reader.pages[0], (0x33, 0x66, 0x99))
    assert _wears(reader.pages[1], (0x33, 0x66, 0x99))  # the first upload's thumbnail in the picture's frame
    assert _wears(reader.pages[2], (0x11, 0x88, 0x44))
    tag = response['ETag']
    unchanged = api.get('/api/proposal/covers/', {'picture': 'none'}, HTTP_IF_NONE_MATCH=tag)
    assert unchanged.status_code == 304
    firm_shop.cover(user, label='Third')
    assert api.get('/api/proposal/covers/', {'picture': 'none'}, HTTP_IF_NONE_MATCH=tag).status_code == 200
    assert api.get('/api/proposal/covers/', HTTP_IF_NONE_MATCH=tag)['ETag'] != tag  # another picture, another tag


def test_J35_a_stock_picture_has_a_thumbnail_and_an_unknown_one_none(api):
    found = api.get('/api/proposal/pictures/gold_lights/thumb/')
    assert found.status_code == 200 and found['Content-Type'] == 'image/jpeg'
    assert api.get('/api/proposal/pictures/../thumb/').status_code == 404
    assert api.get('/api/proposal/pictures/nope/thumb/').status_code == 404


def test_J35_the_catalogue_is_in_meta(api):
    pictures = api.get('/api/meta/').json()['proposal']['pictures']
    assert [place['key'] for place in pictures['places']] == ['cover', 'agenda', 'sections', 'closing']
    assert pictures['defaults']['cover'] == 'blue_light'
    assert 'gold_lights' in [entry['key'] for entry in pictures['stock']]


def test_J33_firm_services_refuse_a_missing_cover(user):
    with pytest.raises(Exception, match='No such cover image'):
        cover_services.delete_cover(user, 999999)
