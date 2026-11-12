"""The BOR e-signature (plan.md §5.2, §7.6; B29, B31; Q.9 row 40): a typed name stamps who signed, when and who
recorded it; it clears; a `bor` file counts as on file; a lost deal refuses the signature."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from conftest import write_path_contract
from deals import activity
from deals.services import mark_lost
from documents import services as documents
from intake import services
from intake.models import Intake

pytestmark = pytest.mark.django_db

PDF = b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n'


def bor_of(api, deal):
    return api.get(f'/api/deals/{deal.id}/intake/').json()['bor']


def test_Q3_1_B29_signing_is_recorded_and_reverted(user, deal):
    intake = Intake.objects.create(deal=deal)
    row = write_path_contract(
        user,
        intake,
        lambda: services.sign_bor(user, deal.id, 'Jordan Example'),
        lambda found: (found.bor_name, found.bor_signed_by_id),
        lambda: services.sign_bor(user, deal.id, 'Casey Example'),
    )
    assert row.summary == 'Signed the BOR (typed signature)' and row.changes[0]['t'] == f'bor:{deal.id}'


def test_B29_a_typed_name_stamps_who_signed_when_and_who_recorded_it(user, api, deal):
    assert bor_of(api, deal)['on_file'] is False
    body = api.post(f'/api/deals/{deal.id}/intake/sign/', {'name': '  Jordan   Example '}, format='json').json()
    bor = body['bor']
    assert (bor['name'], bor['signed_by'], bor['on_file']) == ('Jordan Example', user.id, True)
    assert bor['signed_at'] and bor['by_name'] == (user.get_full_name() or user.username)
    assert body['activity_id'] and 'bor' not in [gap['key'] for gap in body['ready']['gaps']]
    again = api.post(f'/api/deals/{deal.id}/intake/sign/', {'name': 'Jordan Example'}, format='json').json()
    assert again['activity_id'] is None and again['bor']['signed_at'] == bor['signed_at']


def test_B29_clearing_the_signature_and_undoing_the_clear(user, api, deal):
    services.sign_bor(user, deal.id, 'Jordan Example')
    assert api.delete(f'/api/deals/{deal.id}/intake/sign/').status_code == 204
    assert bor_of(api, deal)['on_file'] is False
    cleared = activity.Activity.objects.filter(deal=deal, action='bor').latest('id')
    assert cleared.summary == 'Cleared the BOR signature'
    activity.revert(cleared.id, user)
    assert bor_of(api, deal)['name'] == 'Jordan Example'
    assert api.delete(f'/api/deals/{deal.id}/intake/sign/').status_code == 204
    assert services.clear_bor(user, deal.id).activity is None  # nothing to clear


def test_B29_a_signer_name_is_needed(api, deal):
    for body in ({}, {'name': '   '}, {'name': 'x' * 201}):
        assert api.post(f'/api/deals/{deal.id}/intake/sign/', body, format='json').status_code == 400


def test_B31_a_bor_letter_on_the_deal_puts_the_bor_on_file(user, api, deal):
    documents.upload(user, deal, SimpleUploadedFile('BOR letter (synthetic).pdf', PDF), {'kind': 'bor'})
    body = api.get(f'/api/deals/{deal.id}/intake/').json()
    assert body['bor']['on_file'] is True and body['bor']['signed_at'] is None
    assert [d['name'] for d in body['bor']['files']] == ['BOR letter (synthetic).pdf']
    compliance = {row['kind']: row for row in body['compliance']}
    assert list(compliance) == ['bor', 'carrier_auth', 'claims', 'form_5500', 'plan_doc']
    assert compliance['bor']['label'] == 'Broker of Record letter' and len(compliance['bor']['documents']) == 1


def test_A19_a_lost_deal_refuses_the_signature_but_clears_it(user, api, deal):
    services.sign_bor(user, deal.id, 'Jordan Example')
    mark_lost(user, deal.id)
    answer = api.post(f'/api/deals/{deal.id}/intake/sign/', {'name': 'Casey Example'}, format='json')
    assert answer.status_code == 409 and 'reopen it before signing' in answer.json()['detail']
    assert api.delete(f'/api/deals/{deal.id}/intake/sign/').status_code == 204
