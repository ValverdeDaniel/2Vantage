"""Questionnaires on the portal (plan.md §7.14, §8.20; G83–G98, L91; OQ80, OQ84, OQ85; Q.9 row 58: portal narrowing,
the second factor both ways, officer signing): exactly the allowlisted card, answers that wait for a person, rows the
link added, the paper copy, the blank, the spec the browser may keep, and the officer's signature. Synthetic data."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from deals.models import Activity
from deals.services import mark_lost
from intake.services.checklist import set_checklist_item
from questionnaire.models import Questionnaire
from questionnaire.services import sign_from_link
from questionnaire.tests.world import make_world
from synthetic_files import text_pdf

from .portal_world import client, fresh, make_request, page, save, url, verified

pytestmark = pytest.mark.django_db

FL = 'fl_blue_51'
ONLINE = {'questionnaires': [{'form': FL, 'mode': 'online'}]}
UPLOAD = {'questionnaires': [{'form': FL, 'mode': 'upload'}]}
NARROWED = {'questionnaires': [{'form': FL, 'mode': 'online', 'picks': {'fields': ['txtRsnBid'], 'blocks': []}}]}
CARD = {'form', 'title', 'subtitle', 'kind', 'version', 'mode', 'narrowed', 'blank', 'signed', 'locked', 'sign',
        'state', 'file'}  # fmt: skip
STATE = {'values', 'bases', 'rows', 'blocks', 'order', 'blanks', 'options', 'progress', 'broker', 'colleague'}
REQUIRED = {'dteAnnivDate': '2027-04-01', 'chkFBPrior': 'No', 'txtRsnBid': 'Renewal Increase', 'chkMedCon': 'No'}


@pytest.fixture
def world(user):
    return make_world(user)


def opened(user, deal, asks):
    """(link, token, api, headers): a link asking `asks`, its PIN proved when it has one."""
    link, token, pin = make_request(user, deal, asks)
    api = client()
    headers = verified(api, token, pin) if pin else {}
    return link, token, api, headers


def card_of(body, form=FL):
    return next(one for one in body['questionnaires'] if one['form'] == form)


def answers(card, values):
    """{ref: {value, base}} for the client's answers on one form, with the bases the page read."""
    bases = card['state']['bases']
    return {f'q:{card["form"]}:{slot}': {'value': v, 'base': bases[slot]} for slot, v in values.items()}


def test_G96_OQ80_a_form_online_needs_the_pin_and_a_signed_copy_does_not(user, world):
    _link, token, _pin = make_request(user, world, ONLINE)
    assert page(client(), token).status_code == 428
    link, token, _pin = make_request(user, world, UPLOAD)
    assert link.security == 'link'
    body = page(client(), token).json()
    paper = card_of(body)
    assert paper['mode'] == 'upload' and paper['state'] is None and paper['sign'] is None
    assert paper['file']['slot'] == f'qform:{FL}'


def test_G83_L108_the_card_carries_exactly_its_allowlisted_keys(user, world):
    _link, token, api, headers = opened(user, world, ONLINE)
    body = page(api, token, **headers).json()
    card = card_of(body)
    assert set(card) == CARD and set(card['state']) == STATE
    assert card['sign']['attestation'] and card['blank'] is True and card['narrowed'] is False
    assert 'sources' not in str(card) and 'by_name' not in str(card)
    rail = [item for item in body['checklist']['items'] if item['kind'] == 'questionnaire']
    assert rail and rail[0]['key'] == f'questionnaire_{FL}' and rail[0]['done'] is False


def test_G83_a_waived_form_is_dropped_from_the_page(user, world):
    _link, token, api, headers = opened(user, world, ONLINE)
    set_checklist_item(user, world.id, 'medical_questionnaire', requirement='waived')
    body = page(api, token, **headers).json()
    assert body['questionnaires'] == []


def test_G88_OQ84_answers_on_the_link_wait_and_the_save_answers_the_form_again(user, world):
    link, token, api, headers = opened(user, world, ONLINE)
    card = card_of(page(api, token, **headers).json())
    answer = save(api, token, answers(card, {'txtRsnBid': 'Renewal Increase'}), **headers)
    assert answer.status_code == 200, answer.content
    body = answer.json()
    assert body['saved'] == [f'q:{FL}:txtRsnBid']
    assert body['questionnaires'][FL]['values']['txtRsnBid'] == 'Renewal Increase'
    row = Questionnaire.objects.get(deal=world, form=FL)
    assert 'txtRsnBid' not in row.answers and row.client['txtRsnBid']['link'] == link.id
    saved = Activity.objects.filter(deal=world, area='review', action='client_saved').latest('id')
    assert 'Renewal Increase' not in str(saved.changes) + saved.summary  # key-only (§3.8)


def test_G86_G88_a_broker_field_and_a_bad_answer_are_refused_by_ref(user, world):
    _link, token, api, headers = opened(user, world, ONLINE)
    card = card_of(page(api, token, **headers).json())
    assert 'txtagentname' in card['state']['broker']
    refused = save(api, token, {f'q:{FL}:txtagentname': {'value': 'Someone', 'base': ''}}, **headers)
    assert refused.status_code == 400 and f'q:{FL}:txtagentname' in refused.json()['answers']
    refused = save(api, token, answers(card, {'numTAP': 'lots'}), **headers)
    assert refused.status_code == 400 and f'q:{FL}:numTAP' in refused.json()['answers']


def test_G22_a_narrowed_link_shows_and_takes_only_its_questions(user, world):
    _link, token, api, headers = opened(user, world, NARROWED)
    card = card_of(page(api, token, **headers).json())
    assert card['narrowed'] is True and card['sign'] is None and card['file'] is None and card['blank'] is False
    assert 'txtRsnBid' in card['state']['order'] and 'chkMedCon' not in card['state']['order']
    refused = save(api, token, {f'q:{FL}:chkMedCon': {'value': 'No', 'base': ''}}, **headers)
    assert refused.status_code == 400
    spec = api.get(url(token, f'questionnaires/{FL}/spec/'), **headers)
    assert spec.status_code == 200 and spec['Cache-Control'] == 'private, max-age=3600'
    fields = [field['key'] for section in spec.json()['sections'] for field in section['fields']]
    assert 'txtRsnBid' in fields and 'chkMedCon' not in fields
    assert api.get(url(token, f'questionnaires/{FL}/blank/'), **headers).status_code == 404


def test_G84_the_blank_carrier_form_and_the_spec_for_a_whole_form(user, world):
    _link, token, api, headers = opened(user, world, ONLINE)
    blank = api.get(url(token, f'questionnaires/{FL}/blank/'), **headers)
    assert blank.status_code == 200 and blank['Content-Type'] == 'application/pdf'
    assert b''.join(blank.streaming_content).startswith(b'%PDF')
    spec = api.get(url(token, f'questionnaires/{FL}/spec/'), **headers).json()
    signature = next(section for section in spec['sections'] if section['key'] == 'signature')
    assert signature['intro'] == ''  # the attestation stands beside the sign box instead
    assert any(field.get('broker') for field in signature['fields'])


def test_G87_rows_the_link_adds_and_takes_off(user, world):
    _link, token, api, headers = opened(user, world, ONLINE)
    added = api.post(url(token, f'questionnaires/{FL}/rows/'), {'block': 'plans'}, format='json', **headers)
    assert added.status_code == 201, added.content
    row_id = added.json()['row_id']
    mine = [row for row in added.json()['state']['rows']['plans'] if row['id'] == row_id]
    assert mine and mine[0]['mine'] is True
    gone = api.delete(url(token, f'questionnaires/{FL}/rows/plans/{row_id}/'), **headers)
    assert gone.status_code == 200
    assert row_id not in [row['id'] for row in gone.json()['state']['rows']['plans']]
    first = added.json()['state']['rows']['plans'][0]['id']
    assert api.delete(url(token, f'questionnaires/{FL}/rows/plans/{first}/'), **headers).status_code == 409


def test_G90_G92_a_paper_copy_files_as_the_forms_kind_with_its_link(user, world):
    link, token, api, headers = opened(user, world, ONLINE)
    upload = SimpleUploadedFile('our questionnaire.pdf', text_pdf(['Synthetic filled copy']))
    answer = api.post(url(token, 'files/'), {'slot': f'qform:{FL}', 'file': upload}, **headers)
    assert answer.status_code == 201, answer.content
    document = world.documents.get(source='client')
    assert (document.kind, document.link_id, document.slot) == ('questionnaire', link.id, f'qform:{FL}')
    card = card_of(page(api, token, **headers).json())
    assert [entry['name'] for entry in card['file']['received']] == ['our questionnaire.pdf']


def test_G93_the_officer_signs_on_the_link_held_by_blanks_then_anyway(user, world):
    link, token, api, headers = opened(user, world, ONLINE)
    sign = url(token, f'questionnaires/{FL}/sign/')
    held = api.post(sign, {'name': 'Robin Example'}, format='json', **headers)
    assert held.status_code == 409 and held.json()['incomplete']['total'] > held.json()['incomplete']['filled']
    card = card_of(page(api, token, **headers).json())
    save(api, token, answers(card, REQUIRED), **headers)
    signed = api.post(sign, {'name': 'Robin Example'}, format='json', **headers)
    assert signed.status_code == 200, signed.content
    card = signed.json()['questionnaire']
    assert card['signed']['name'] == 'Robin Example' and card['locked'] is True and card['sign'] is None
    row = Questionnaire.objects.get(deal=world, form=FL)
    assert row.officer_link == link.id and all(entry['status'] == 'pending' for entry in row.client.values())
    assert fresh(link).last_saved_at is not None
    later = save(api, token, {f'q:{FL}:txtRsnBid': {'value': 'Other', 'base': ''}}, **headers)
    assert later.status_code == 400  # a signed form takes nothing more
    items = page(api, token, **headers).json()['checklist']['items']
    assert next(item for item in items if item['kind'] == 'questionnaire')['done'] is True


def test_G97_a_lost_deal_reads_but_refuses_every_form_write(user, world):
    _link, token, api, headers = opened(user, world, ONLINE)
    mark_lost(user, world.id, reason='Went elsewhere')
    assert page(api, token, **headers).status_code == 200
    rows = api.post(url(token, f'questionnaires/{FL}/rows/'), {'block': 'plans'}, format='json', **headers)
    assert rows.status_code == 410
    sign = api.post(url(token, f'questionnaires/{FL}/sign/'), {'name': 'Robin Example'}, format='json', **headers)
    assert sign.status_code == 410


def test_G97_a_signature_moves_the_pages_stamp(user, world):
    link, token, api, headers = opened(user, world, ONLINE)
    before = api.get(url(token, 'stamp/'), **headers).json()['form_stamp']
    sign_from_link(world.id, link.id, FL, 'Robin Example', sign_anyway=True)
    assert api.get(url(token, 'stamp/'), **headers).json()['form_stamp'] != before
