"""Printed page numbers (plan.md §6.3; E94; the old ai/page_labels.py, D-149): the number a carrier printed on a page,
where it differs from the page's place in the PDF. Pure: synthetic PDFs, numbers only."""

import pytest

from documents.pages import printed_labels
from documents.services import set_page_labels
from synthetic_files import pdf


def page(*lines):
    return [(40, 700 - 20 * at, text, 10) for at, text in enumerate(lines)]


def test_E94_a_packet_numbered_anew_maps_its_pdf_pages_to_the_printed_numbers():
    raw = pdf([page('Dear benefits partner,'), page('Plan options', 'Rates', 'Page 1 of 2'), page('Terms', '2')])
    assert printed_labels(raw) == {'2': '1', '3': '2'}


@pytest.mark.parametrize(
    'footer', ['Page 2 of 2', '2', '2 - Confidential and Proprietary', 'Confidential - 2', 'page 2']
)
def test_E94_the_printed_number_is_read_from_the_old_patterns(footer):
    raw = pdf([page('Cover letter'), page('Terms', 'More terms'), page('Rates', footer)])
    assert printed_labels(raw) == {'3': '2'}


def test_E94_pages_that_print_their_own_number_or_none_have_no_labels():
    assert printed_labels(pdf([page('Cover', '1'), page('Rates', 'Page 2 of 2')])) == {}
    assert printed_labels(pdf([page('No numbers here'), page('Nor here')])) == {}
    assert printed_labels(b'not a pdf') == {}


@pytest.mark.django_db
def test_E94_set_page_labels_writes_only_when_they_differ(user, deal):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from documents.services import upload

    raw = pdf([page('Cover'), page('Rates', 'Page 1 of 1')])
    document = upload(user, deal, SimpleUploadedFile('Quote (synthetic).pdf', raw), {'kind': 'quote'})
    assert set_page_labels(document.id, deal, {'2': '1'}) is True
    assert set_page_labels(document.id, deal, {'2': '1'}) is False
    document.refresh_from_db()
    assert document.page_labels == {'2': '1'}
