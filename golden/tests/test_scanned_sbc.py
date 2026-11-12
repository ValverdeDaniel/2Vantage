"""GD4's scanned SBC (plan.md §10.7, §13.10 row 65; E25, OQ98; golden/scanned_sbc.py). The file is a picture of a page:
nothing on the server reads it, so "Check this file" leaves its values to the eye (never found, never "not in the
file"), and only the station's browser OCR draws where they are, writing nothing (Q.9 row 65)."""

import pytest

from documents import pages
from documents.models import Document
from quotes.models import Plan

pytestmark = pytest.mark.django_db

PRINTED = ('deductible_single', 'oop_max_single')


def _sbc(gd4):
    return Document.objects.get(deal=gd4.deal, kind='sbc')


def test_E25_GD4_carries_P1s_SBC_as_a_scan_with_no_text_layer(golden, api):
    gd4 = golden['GD4']
    sbc = _sbc(gd4)
    assert (sbc.page_count, sbc.role, sbc.carrier, sbc.lines) == (1, 'current', 'Aetna', ['medical'])
    with sbc.file.open('rb') as handle:
        assert [text.strip() for text in pages.page_texts(handle.read())] == ['']
    plan = gd4.refs['P1']
    for key in PRINTED:
        body = api.get(f'/api/plans/{plan}/source/', {'key': key}).json()
        assert body['source']['doc'] == sbc.id, key
        assert body['value'] == gd4.spec['plans'][0]['values'][key]


def test_E25_check_this_file_leaves_a_scanned_page_to_the_eye(golden, api):
    gd4 = golden['GD4']
    sbc = _sbc(gd4)
    answer = api.post(f'/api/deals/{gd4.deal.id}/ai/locate/', {'document_ids': [sbc.id]}, format='json')
    assert answer.status_code in (200, 201)
    job = answer.json()
    assert job['status'] == 'done'
    assert job['counts']['found'] == 0 and job['counts']['absent'] == 0
    sources = Plan.objects.get(pk=gd4.refs['P1']).sources
    for key in PRINTED:
        loc = sources[key]['loc']
        assert (loc['state'], loc['why']) == ('nocheck', 'no_text'), key
    # The station's file bar reads this answer: "Check by eye", whatever the browser's OCR then draws.
    body = api.get(f'/api/plans/{gd4.refs["P1"]}/source/', {'key': PRINTED[0]}).json()
    assert body['source']['loc']['state'] == 'nocheck'
