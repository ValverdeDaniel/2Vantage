"""Paper and the Letter PDF (plan.md §9.7, §13.8 row 30, "done when": Paper shows the Letter frame; J114, J115; Q.9 row
30: paper scale)."""

import io

import pytest
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from deals.models import Activity
from proposals.layout import tokens
from proposals.paint import paper


def test_S30_J114_a_slide_prints_at_three_quarters_inside_a_half_inch_margin_centred():
    place = paper.placement(*tokens.DECK_SIZE)
    assert place['sheet'] == paper.LETTER_LANDSCAPE and not place['as_is']
    assert place['scale'] == pytest.approx(0.75)
    width, height = (side * place['scale'] for side in tokens.DECK_SIZE)
    assert place['x'] == pytest.approx((792 - width) / 2) and place['x'] >= paper.MARGIN
    assert place['y'] == pytest.approx((612 - height) / 2) and place['y'] >= paper.MARGIN
    assert paper.summary(*tokens.DECK_SIZE) == {'scale': 75.0, 'sheet': 'landscape', 'as_is': False, 'inner': 0.9091}


def test_S30_J114_a_letter_page_prints_as_it_is_either_way_round_and_a_tall_page_on_portrait():
    assert paper.placement(612, 792) == {'sheet': (612.0, 792.0), 'scale': 1.0, 'x': 0.0, 'y': 0.0, 'as_is': True}
    assert paper.placement(792.4, 611.8)['as_is'] is True
    tall = paper.summary(595, 842)  # an A4 page goes on Letter portrait, shrunk to the half-inch margin
    assert tall['sheet'] == 'portrait' and not tall['as_is'] and tall['scale'] < 100


def _two_pages():
    out = io.BytesIO()
    pdf = canvas.Canvas(out, pagesize=tokens.DECK_SIZE)
    pdf.setTitle('Synthetic Client — Employee Benefits Proposal')
    pdf.drawString(72, 300, 'Slide one words')
    pdf.showPage()
    pdf.setPageSize((612, 792))
    pdf.drawString(72, 700, 'A letter page')
    pdf.showPage()
    pdf.save()
    return out.getvalue()


def test_S30_J115_the_letter_pdf_puts_each_slide_on_a_sheet_of_its_own_and_a_letter_page_through():
    reader = PdfReader(io.BytesIO(paper.letter(_two_pages())))
    sizes = [(float(page.mediabox.width), float(page.mediabox.height)) for page in reader.pages]
    assert sizes == [paper.LETTER_LANDSCAPE, (612.0, 792.0)]
    assert 'Slide one words' in reader.pages[0].extract_text()
    assert 'A letter page' in reader.pages[1].extract_text()
    assert reader.metadata.title == 'Synthetic Client — Employee Benefits Proposal'


@pytest.mark.django_db
def test_S30_J115_GD1s_letter_pdf_is_the_pdf_download_on_letter_sheets_page_for_page(api, gd1):
    before = Activity.objects.filter(deal=gd1.deal).count()
    response = api.get(f'/api/deals/{gd1.deal.id}/proposal/files/letter/')
    assert response.status_code == 200 and response['Content-Type'] == 'application/pdf'
    disposition = response['Content-Disposition']
    assert disposition.startswith('attachment;') and 'Benefits Proposal-DRAFT Letter.pdf' in disposition
    letter = PdfReader(io.BytesIO(b''.join(response.streaming_content)))
    assert Activity.objects.filter(deal=gd1.deal).count() == before + 1  # its `downloaded` row
    download = api.get(f'/api/deals/{gd1.deal.id}/proposal/files/pdf/')
    pages = PdfReader(io.BytesIO(b''.join(download.streaming_content))).pages
    assert len(letter.pages) == len(pages)
    for sheet, page in zip(letter.pages, pages, strict=True):
        assert (float(sheet.mediabox.width), float(sheet.mediabox.height)) == paper.LETTER_LANDSCAPE
        assert ' '.join(sheet.extract_text().split()) == ' '.join(page.extract_text().split())
