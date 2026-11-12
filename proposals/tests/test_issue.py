"""Issue to client on GD1 (plan.md §13.8 row 32, "done when": Issue makes v1 with three stored files and moves the
deal to Proposal; v2 leaves v1's bytes unchanged; an uncovered shopped line is refused with its sentence; Q.9 row 32;
J102–J104, J159, OQ35). `gd1` is built once for the module; each test's writes roll back with its transaction."""

import io
import zipfile

import openpyxl
import pytest
from pptx import Presentation
from pypdf import PdfReader

from deals.models import Activity, Deal
from documents.models import Document
from proposals import ready, services
from proposals.issues import catalog
from quotes import services as plans

pytestmark = pytest.mark.django_db

DRAFT = ready.DRAFT_MARK


def _issue(api, deal):
    response = api.post(f'/api/deals/{deal.id}/proposal/issue/', {}, format='json')
    assert response.status_code == 202, response.content
    return response.json()


def _stored(api, deal, version, file):
    response = api.get(f'/api/deals/{deal.id}/proposal/issues/{version}/{file}/')
    assert response.status_code == 200, file
    return response, b''.join(response.streaming_content)


def _predicted(api, deal):
    found = {}
    for line in ('medical', 'dental', 'vision'):
        body = api.get(f'/api/deals/{deal.id}/proposal/pages/', {'line': line, 'preset': 'key'}).json()
        found.update({plan['plan_id']: plan['option'] for plan in body['plans'] if plan['option']})
    return found


def _pptx_words(data):
    deck = Presentation(io.BytesIO(data))
    owners = [deck.slide_master, *deck.slide_layouts, *deck.slides]
    return ' '.join(shape.text_frame.text for owner in owners for shape in owner.shapes if shape.has_text_frame)


def test_J103_J102_GD1_issue_makes_v1_with_three_stored_protected_files_and_moves_the_deal_to_proposal(api, gd1):
    deal = gd1.deal
    predicted = _predicted(api, deal)
    body = _issue(api, deal)
    assert (body['version'], body['state']) == (1, 'issued')
    assert [entry['key'] for entry in body['files']] == list(catalog.FILE_KEYS)
    documents = Document.objects.filter(deal=deal, kind='proposal')
    assert sorted(documents.values_list('label', flat=True)) == sorted(
        f'Proposal v1 · {label}' for label in catalog.LABELS.values()
    )
    assert all(document.protected for document in documents)
    assert Deal.objects.get(pk=deal.pk).stage == 'proposal'
    # OQ35: the numbers the drafts predicted are the ones stamped, and the issue recorded them (quotes' stamp did not)
    stamped = Activity.objects.get(deal=deal, area='proposal', summary__startswith='Stamped')
    recorded = {int(entry['t'].split(':')[1]): entry['k']['plan.option_number'][1] for entry in stamped.changes}
    assert recorded == predicted
    issued = Activity.objects.get(deal=deal, area='proposal', summary='Issued proposal v1')
    assert issued.document_id == body['files'][0]['document_id'] and not issued.revertible
    # J102, J104: no Draft anywhere in what the client gets, "Version 1" in the deck's footer, no -DRAFT in the names
    response, pdf = _stored(api, deal, 1, 'pdf')
    assert 'DRAFT' not in response['Content-Disposition']
    texts = ' '.join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
    assert DRAFT not in texts and 'Version 1' in texts
    pptx = _stored(api, deal, 1, 'pptx')[1]
    assert DRAFT not in _pptx_words(pptx) and 'Version 1' in _pptx_words(pptx)
    book = openpyxl.load_workbook(io.BytesIO(_stored(api, deal, 1, 'xlsx')[1]))
    assert not any(DRAFT in (sheet.oddHeader.center.text or '') for sheet in book.worksheets)
    builder = api.get(f'/api/deals/{deal.id}/proposal/').json()
    assert [(row['version'], row['state']) for row in builder['issues']] == [(1, 'issued')]


def test_J103_GD1_v2_leaves_v1s_bytes_unchanged(api, user, gd1):
    deal = gd1.deal
    _issue(api, deal)
    first = {file: _stored(api, deal, 1, file)[1] for file in catalog.FILE_KEYS}
    services.set_config(user, deal, {'title': 'Second thoughts (synthetic)'})
    second = _issue(api, deal)
    assert second['version'] == 2
    assert {file: _stored(api, deal, 1, file)[1] for file in catalog.FILE_KEYS} == first
    later = _stored(api, deal, 2, 'pdf')[1]
    assert later != first['pdf']
    assert 'Version 2' in ' '.join(page.extract_text() for page in PdfReader(io.BytesIO(later)).pages)
    listed = api.get(f'/api/deals/{deal.id}/proposal/issues/').json()
    assert [row['version'] for row in listed] == [2, 1]


def test_J28_J103_GD1_an_uncovered_shopped_line_is_refused_with_its_sentence(api, user, gd1):
    deal, refs = gd1.deal, gd1.refs
    plans.set_recommended(user, refs['VS2'], False)
    response = api.post(f'/api/deals/{deal.id}/proposal/issue/', {}, format='json')
    assert response.status_code == 409
    sentence = ready.sentence(['Vision'])
    assert response.json() == {'detail': sentence, 'blockers': [sentence]}
    assert not deal.proposal_issues.exists()
    assert not Activity.objects.filter(deal=deal, area='proposal', action='issued').exists()
    assert Deal.objects.get(pk=deal.pk).stage != 'proposal'


def test_J96_J114_GD1_the_packet_and_the_letter_come_from_the_stored_bytes(api, gd1):
    deal = gd1.deal
    _issue(api, deal)
    stored = {file: _stored(api, deal, 1, file) for file in catalog.FILE_KEYS}
    zipped = zipfile.ZipFile(io.BytesIO(_stored(api, deal, 1, 'packet')[1]))
    names = {
        response['Content-Disposition'].split('filename="')[1].rstrip('"'): data for response, data in stored.values()
    }
    assert {name: zipped.read(name) for name in zipped.namelist()} == names
    only = zipfile.ZipFile(
        io.BytesIO(api.get(f'/api/deals/{deal.id}/proposal/issues/1/packet/?include=xlsx').getvalue())
    )
    assert [name.endswith('.xlsx') for name in only.namelist()] == [True]
    refused = api.get(f'/api/deals/{deal.id}/proposal/issues/1/packet/', {'include': ''})
    assert refused.status_code == 409 and refused.json()['detail'] == 'Tick at least one file for the packet.'
    response, letter = _stored(api, deal, 1, 'letter')
    reader = PdfReader(io.BytesIO(letter))
    assert len(reader.pages) == len(PdfReader(io.BytesIO(stored['pdf'][1])).pages)
    assert (float(reader.pages[0].mediabox.width), float(reader.pages[0].mediabox.height)) == (792.0, 612.0)
    assert 'Letter' in response['Content-Disposition'] and 'DRAFT' not in response['Content-Disposition']
    rows = Activity.objects.filter(deal=deal, action='downloaded', summary__contains='(v1)')
    assert rows.count() >= 5 and all(row.document_id for row in rows)
