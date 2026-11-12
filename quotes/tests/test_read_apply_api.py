"""The doors of a used read (plan.md §7.5; D72, D73): `ai/jobs/{id}/apply/` and `…/undo/` on GD3's packet, and the
"✓ Used … ↶ Undo this run" entry the deal's AI state carries while it is fresh."""

import hashlib

import pytest

from documents.models import Document
from quotes import services as plans
from quotes.models import Plan

pytestmark = pytest.mark.django_db


@pytest.fixture
def waiting(api, quote_first, gd3_packet_answer, fake_claude):
    deal = quote_first.built.deal
    document = Document.objects.get(deal=deal, kind='renewal')
    with document.file.open('rb') as handle:
        key = ('quotes', hashlib.sha256(handle.read()).hexdigest()[:16], gd3_packet_answer[1])
    fake_claude.record(key, gd3_packet_answer[0])
    job = api.post(f'/api/deals/{deal.id}/ai/reads/', {'document_ids': [document.id]}, format='json').json()
    return deal, job


def test_D72_apply_answers_the_job_and_what_landed(api, waiting):
    deal, job = waiting
    answer = api.post(f'/api/ai/jobs/{job["id"]}/apply/', {}, format='json')
    assert answer.status_code == 200
    body = answer.json()
    assert body['job']['resolution'] == 'applied' and body['job']['activity_id'] == body['landed']['activity_id']
    assert body['landed']['summary'] == '2 current plans · 2 renewals' and len(body['landed']['created']) == 4
    state = api.get(f'/api/deals/{deal.id}/ai/').json()
    assert state['waiting'] == [] and [(n['type'], n['job_id']) for n in state['news']] == [('landed', job['id'])]
    assert api.post(f'/api/ai/jobs/{job["id"]}/apply/', {}, format='json').status_code == 409


def test_D31_apply_refuses_an_unknown_item_with_a_400(api, waiting):
    _deal, job = waiting
    answer = api.post(f'/api/ai/jobs/{job["id"]}/apply/', {'select': ['nope']}, format='json')
    assert answer.status_code == 400 and 'select' in answer.json()


def test_D73_undo_answers_what_it_did_and_keeps_a_plan_sold_since(api, user, waiting):
    deal, job = waiting
    select = [item['id'] for item in api.get(f'/api/ai/jobs/{job["id"]}/').json()['result']['items']]
    landed = api.post(f'/api/ai/jobs/{job["id"]}/apply/', {'select': select[:4]}, format='json').json()['landed']
    current = Plan.objects.get(id=landed['created'][0])
    plans.set_sold(user, current.id, True)  # a plan the read made, sold since: it stays (D73)

    answer = api.post(f'/api/ai/jobs/{job["id"]}/undo/', {}, format='json')

    assert answer.status_code == 200
    assert answer.json()['undone']['kept'] == [f'{current.carrier} {current.name}']
    assert api.get(f'/api/deals/{deal.id}/ai/').json()['news'] == []
    assert api.post(f'/api/ai/jobs/{job["id"]}/undo/', {}, format='json').status_code == 200  # once; again is a no-op


def test_D73_undo_refused_says_undo_anyway_can_work(api, user, waiting):
    _deal, job = waiting
    items = api.get(f'/api/ai/jobs/{job["id"]}/').json()['result']['items']
    counts = [item['id'] for item in items if item['op'] == 'summary_counts']
    plan_items = [item['id'] for item in items if item['op'] == 'create_plan']
    landed = api.post(f'/api/ai/jobs/{job["id"]}/apply/', {'select': plan_items + counts}, format='json').json()
    figure = {'EE': 31, 'ES': 8, 'EC': 6, 'FAM': 8}
    plans.set_enrollment(user, Plan.objects.get(id=landed['landed']['created'][0]).deal, 'medical', whole_line=figure)

    refused = api.post(f'/api/ai/jobs/{job["id"]}/undo/', {}, format='json')
    assert refused.status_code == 409 and refused.json()['can_force'] == 'true'
    forced = api.post(f'/api/ai/jobs/{job["id"]}/undo/', {'force': True}, format='json')
    assert forced.status_code == 200 and forced.json()['undone']['skipped']
    assert not Plan.objects.filter(id__in=landed['landed']['created']).exists()
