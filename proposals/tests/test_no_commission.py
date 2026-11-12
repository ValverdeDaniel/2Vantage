"""Client files never carry commission (plan.md §9.15, §12.9; H125): GD1-sold's issued PDF, PowerPoint and workbook,
built from a deal whose sale booked two records, hold no booked figure, no share and no word of commission."""

import io
import re

import openpyxl
import pytest
from pptx import Presentation
from pypdf import PdfReader

from commission import selectors
from proposals.issues import build

pytestmark = pytest.mark.django_db


def _pdf(data):
    return ' '.join(page.extract_text() or '' for page in PdfReader(io.BytesIO(data)).pages)


def _pptx(data):
    deck = Presentation(io.BytesIO(data))
    return ' '.join(shape.text_frame.text for slide in deck.slides for shape in slide.shapes if shape.has_text_frame)


def _xlsx(data):
    book = openpyxl.load_workbook(io.BytesIO(data))
    return ' '.join(str(cell.value) for sheet in book for row in sheet.iter_rows() for cell in row if cell.value)


def test_H125_client_files_carry_no_commission(gd1_sold, admin_user):
    deal, _refs, _spec = gd1_sold
    booking = selectors.deal_payload(deal, admin_user)['booking']
    figures = {row['expected'] for row in booking['records']} | {booking['totals']['expected']}
    figures |= {share['amount'] for row in booking['records'] for share in row['shares']}
    words = [f'{figure:,.2f}'.rstrip('0').rstrip('.') for figure in figures if figure]
    words += [f'{figure:,}' for figure in figures if figure and figure == int(figure)]
    files = build.files(deal, 1)
    for key, read in (('pdf', _pdf), ('pptx', _pptx), ('xlsx', _xlsx)):
        text = read(files[key][1])
        assert not re.search(r'commission', text, re.IGNORECASE), key
        for word in words:
            assert word not in text, (key, word)
