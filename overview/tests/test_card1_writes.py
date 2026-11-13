"""Slice 63's done-when (plan.md §13 row 63; Q.9 row 63; M.6 O3): every Card 1 control writes through its owning app.
Each test presses one control the way the card does — the On file and Confirmed ticks, Not needed, Still needed ▸ and
Undo (intake's checklist door), ⬆ Attach (documents' upload), the form pickers (the questionnaire's choice door), ＋ Ask
and ＋ Ask for their census file (review's tray) — then reads the Overview again and finds the change where its owner
keeps it. The Overview itself has no door (O.2). Synthetic only."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

import synthetic_files
from deals.models import Activity

pytestmark = pytest.mark.django_db

PDF = synthetic_files.text_pdf(['Example Health renewal (synthetic)'], ['Rates follow.'])


def overview(api, deal):
    response = api.get(f'/api/deals/{deal.id}/overview/')
    assert response.status_code == 200, response.content
    return response.json()


def item(api, deal, group_key, key):
    group = next(found for found in overview(api, deal)['get_to_market']['groups'] if found['key'] == group_key)
    if 'item' in group:
        return group['item']
    return next(found for found in group['items'] if found['key'] == key)


def checklist(api, deal, body):
    response = api.patch(f'/api/deals/{deal.id}/intake/checklist/', body, format='json')
    assert response.status_code == 200, response.content
    return response.json()


def test_M53_on_file_is_intakes_tick_and_card_1_reads_it_back(api, deal):
    assert item(api, deal, 'documents', 'renewal')['done'] is False
    checklist(api, deal, {'item': 'renewal', 'checked': True})
    found = item(api, deal, 'documents', 'renewal')
    assert (found['attested'], found['done'], found['status']) == (True, True, 'done')
    assert Activity.objects.filter(deal=deal, area='intake', action='checklist').exists()


def test_M60_confirmed_is_intakes_tick_too(api, deal):
    checklist(api, deal, {'item': 'cobra', 'checked': True})
    group = next(found for found in overview(api, deal)['get_to_market']['groups'] if found['key'] == 'confirmations')
    assert group['met'] is True and group['count'] == '1/1'


def test_M55_not_needed_still_needed_and_undo_are_intakes_requirement(api, deal):
    checklist(api, deal, {'item': 'invoice', 'requirement': 'waived'})
    assert item(api, deal, 'documents', 'invoice')['waived'] is True
    checklist(api, deal, {'item': 'invoice', 'requirement': 'required', 'client_note': 'This year’s, please.'})
    forced = item(api, deal, 'documents', 'invoice')
    assert (forced['forced'], forced['client_note'], forced['done']) == (True, 'This year’s, please.', False)
    checklist(api, deal, {'item': 'invoice', 'requirement': ''})
    undone = item(api, deal, 'documents', 'invoice')
    assert (undone['forced'], undone['waived'], undone['status']) == (False, False, 'missing')


def test_M52_attach_uploads_through_documents_and_the_row_reads_on_file(api, deal):
    upload = SimpleUploadedFile('Renewal (synthetic).pdf', PDF)
    response = api.post(f'/api/deals/{deal.id}/documents/', {'file': upload, 'kind': 'renewal'}, format='multipart')
    assert response.status_code == 201, response.content
    found = item(api, deal, 'documents', 'renewal')
    assert (found['has_document'], found['done']) == (True, True)


def test_M51_M56_the_form_pickers_write_through_the_questionnaires_choice(api, deal):
    path = f'/api/deals/{deal.id}/questionnaires/choice/'
    response = api.patch(path, {'item': 'medical_questionnaire', 'choice': 'fl_blue_51'}, format='json')
    assert response.status_code == 200, response.content
    medical = item(api, deal, 'questionnaire', 'medical_questionnaire')
    assert (medical['form_key'], medical['form_source']) == ('fl_blue_51', 'producer')
    assert medical['form_detail'].endswith('· chosen by you · not started')
    assert item(api, deal, 'stop_loss', 'stop_loss_disclosure')['optional'] is True
    response = api.patch(path, {'item': 'stop_loss_disclosure', 'choice': 'stop_loss_siia'}, format='json')
    assert response.status_code == 200, response.content
    group = next(found for found in overview(api, deal)['get_to_market']['groups'] if found['key'] == 'stop_loss')
    assert (group['offer'], group['met'], group['item']['form_key']) == (False, False, 'stop_loss_siia')


@pytest.mark.parametrize('ref', ['doc:renewal', 'census:file'])
def test_M49_M54_ask_puts_the_item_in_reviews_tray(api, deal, ref):
    response = api.post(f'/api/deals/{deal.id}/review/tray/', {'refs': [ref]}, format='json')
    assert response.status_code in (200, 201), response.content
    tray = api.get(f'/api/deals/{deal.id}/review/tray/').json()
    assert ref in [entry['ref'] for entry in tray['items']]
    assert overview(api, deal)['asks'] == {'refusal': None, 'file_asks_ready': True}


@pytest.mark.parametrize('method', ['post', 'put', 'patch', 'delete'])
def test_O2_the_overview_has_no_door_of_its_own(api, deal, method):
    for path in (f'/api/deals/{deal.id}/overview/', f'/api/deals/{deal.id}/overview/feed/'):
        assert getattr(api, method)(path, {}, format='json').status_code == 405
