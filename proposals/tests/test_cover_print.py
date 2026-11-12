"""Slice 34's "done when" (plan.md §13.8 row 34): an uploaded cover and a team member print on the PDF and the
PowerPoint, through the endpoints a producer uses (J33–J35, J43, J123, J125). Also: the pictures per place, the cover
page switched off, a deleted upload falling back, and the spreadsheet's banner (J145)."""

import io

import pytest
from openpyxl import load_workbook
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pypdf import PdfReader

from proposals.tests import firm_shop

pytestmark = pytest.mark.django_db

HARBOUR = (0x33, 0x66, 0x99)  # the synthetic cover upload's colour
PORTRAIT = (0xAA, 0x55, 0x33)  # the synthetic team photo's colour
NAME = 'Sam Rivera (synthetic)'


def _close(colour, other, slack=14):
    return all(abs(a - b) <= slack for a, b in zip(colour, other, strict=True))


def _flat(picture):
    picture = picture.convert('RGB')
    return picture.getpixel((picture.width // 2, picture.height // 2))


def _download(api, deal, file):
    response = api.get(f'/api/deals/{deal.id}/proposal/files/{file}/')
    assert response.status_code == 200
    return b''.join(response.streaming_content) if response.streaming else response.content


def _pdf(api, deal):
    return PdfReader(io.BytesIO(_download(api, deal, 'pdf')))


def _pdf_wears(page, colour):
    return any(_close(_flat(image.image), colour) for image in page.images)


def _slide_wears(slide, colour):
    from PIL import Image

    for shape in slide.shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            with Image.open(io.BytesIO(shape.image.blob)) as picture:
                if _close(_flat(picture), colour):
                    return True
    return False


def _slide_text(slide):
    return ' '.join(shape.text_frame.text for shape in slide.shapes if shape.has_text_frame)


@pytest.fixture
def dressed(api, user, gd1):
    """GD1 wearing an uploaded cover, with one team member (photo and bio) picked for this client."""
    made = api.post('/api/proposal/cover-images/', {'image': firm_shop.upload('Harbour.jpg', size=(2000, 1300))})
    person = firm_shop.person(user, bio='Twenty years placing benefits.', on_by_default=False)
    firm_shop.person(user, name='Off This Deal (synthetic)', photo=False)
    changes = {'output.cover.image': made.json()['id'], 'team': [person.id]}
    assert api.patch(f'/api/deals/{gd1.deal.id}/proposal/', changes, format='json').status_code == 200
    return gd1.deal


def test_S34_done_when_an_uploaded_cover_and_a_team_member_print_on_the_pdf(api, dressed):
    reader = _pdf(api, dressed)
    texts = [page.extract_text() for page in reader.pages]
    assert 'Golden Manufacturing' in texts[0] and 'Coverage effective' in texts[0]
    assert _pdf_wears(reader.pages[0], HARBOUR)  # the upload stands in the cover's picture frame
    team = next(n for n, text in enumerate(texts) if 'Your team' in text)
    assert NAME in texts[team] and _pdf_wears(reader.pages[team], PORTRAIT)
    joined = ' '.join(texts)
    assert 'Twenty years placing benefits.' in joined  # the bio page
    assert 'Off This Deal' not in joined  # the deal picked its own team (J43)
    assert 'Harbour' not in joined  # an upload's file name never prints


def test_S34_done_when_an_uploaded_cover_and_a_team_member_print_on_the_powerpoint(api, dressed):
    deck = Presentation(io.BytesIO(_download(api, dressed, 'pptx')))
    slides = list(deck.slides)
    assert _slide_wears(slides[0], HARBOUR)
    team = next(slide for slide in slides if 'Your team' in _slide_text(slide))
    assert NAME in _slide_text(team) and _slide_wears(team, PORTRAIT)
    assert not any('Off This Deal' in _slide_text(slide) for slide in slides)


def test_J35_each_dark_page_wears_its_own_pick(api, user, gd1):
    image = firm_shop.cover(user, colour='#118844')
    picks = {
        'output.pictures.closing': f'upload:{image.id}',
        'output.pictures.cover': None,
        'output.pages.agenda': True,
    }
    api.patch(f'/api/deals/{gd1.deal.id}/proposal/', picks, format='json')
    reader = _pdf(api, gd1.deal)
    texts = [page.extract_text() for page in reader.pages]
    thanks = next(n for n, text in enumerate(texts) if 'Thank you' in text)
    assert _pdf_wears(reader.pages[thanks], (0x11, 0x88, 0x44))
    assert not reader.pages[0].images or not _pdf_wears(reader.pages[0], (0x11, 0x88, 0x44))


def test_J34_the_cover_page_switched_off_prints_no_cover(api, gd1):
    api.patch(f'/api/deals/{gd1.deal.id}/proposal/', {'output.cover.on': False}, format='json')
    first = _pdf(api, gd1.deal).pages[0].extract_text()
    assert 'Coverage effective' not in first and 'Prepared' not in first.split('·')[0]


def test_J33_a_deleted_upload_falls_back_to_the_covers_stock_picture(
    api, user, gd1, django_capture_on_commit_callbacks
):
    image = firm_shop.cover(user)
    api.patch(f'/api/deals/{gd1.deal.id}/proposal/', {'output.cover.image': image.id}, format='json')
    with django_capture_on_commit_callbacks(execute=True):
        api.delete(f'/api/proposal/cover-images/{image.id}/')
    reader = _pdf(api, gd1.deal)
    assert not _pdf_wears(reader.pages[0], HARBOUR)
    assert reader.pages[0].images  # the stock picture (blue light) and the logo still print


def test_J145_the_spreadsheet_cover_carries_the_upload_as_its_banner_and_never_a_stock_picture(api, dressed, gd1):
    book = load_workbook(io.BytesIO(_download(api, dressed, 'xlsx')))
    cover = book.worksheets[0] if book.worksheets[0].title == 'Cover' else book['Cover']
    anchors = sorted((image.anchor._from.row, image.anchor._from.col) for image in cover._images)
    assert (0, 1) in anchors  # B1: the banner above the logo
    api.patch(f'/api/deals/{gd1.deal.id}/proposal/', {'output.cover.image': None}, format='json')
    plain = load_workbook(io.BytesIO(_download(api, gd1.deal, 'xlsx')))['Cover']
    assert (0, 1) not in [(image.anchor._from.row, image.anchor._from.col) for image in plain._images]
