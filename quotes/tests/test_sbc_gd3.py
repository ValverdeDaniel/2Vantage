"""Slice 22's "done when" on GD3 (plan.md §13.7 row 22; Q.9 row 22; D38, D47, OQ33): after the renewal packet's read
lands, "Attach SBC…" on the current BlueOptions PPO 2500 stages its design values, the value the SBC disagrees with
is flagged, and nothing changes until a person uses the read. The packet's read and the SBC's are replayed by the
fake client; the SBC is synthetic. Each test builds its own GD3."""

import hashlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from ai import land
from ai import services as ai
from ai.models import Job
from deals.models import Activity
from documents.models import Document
from documents.review_rules import open_warning
from quotes.models import Plan
from quotes.tests.sbc_world import answer, sbc_pdf

pytestmark = pytest.mark.django_db

SBC = {'deductible_single': '2500', 'deductible_family': '5000', 'pcp_copay': '35', 'specialist_copay': '60'}


@pytest.fixture
def landed(quote_first, gd3_packet_answer, fake_claude, admin_user):
    deal = quote_first.built.deal
    packet = Document.objects.get(deal=deal, kind='renewal')
    with packet.file.open('rb') as handle:
        raw = handle.read()
    reply, label = gd3_packet_answer
    fake_claude.record(('quotes', hashlib.sha256(raw).hexdigest()[:16], label), reply)
    job, _created = ai.start_read(admin_user, deal, [packet.id])
    job.refresh_from_db()
    assert job.resolution == 'applied'
    current = Plan.objects.get(deal=deal, role='current', name='BlueOptions PPO 2500')
    return deal, current


def test_S22_attach_sbc_on_gd3_stages_design_values_and_flags_the_disagreement(admin_api, landed, fake_claude):
    deal, current = landed
    raw = sbc_pdf('Florida Blue', 'BlueOptions PPO 2500 (SBC)', {**SBC, 'rate_ee': '999.99'})
    fake_claude.record(
        ('sbc', hashlib.sha256(raw).hexdigest()[:16], 'p1'),
        answer('Florida Blue', 'BlueOptions PPO 2500 (SBC)', {**SBC, 'rate_ee': '999.99'}),
    )
    rows = Activity.objects.filter(deal=deal).count()
    before = Plan.objects.get(pk=current.id).values

    answered = admin_api.post(
        f'/api/plans/{current.id}/sbc/', {'file': SimpleUploadedFile('BlueOptions SBC (synthetic).pdf', raw)}
    )
    assert answered.status_code == 201, answered.content
    job = Job.objects.get(pk=answered.json()['id'])
    assert (job.target, job.land, job.wait_reason) == ('sbc', land.STAGED, land.ALWAYS)  # OQ33, even an admin's
    document = Document.objects.get(pk=job.documents[0])
    assert (document.kind, document.carrier, document.lines) == ('sbc', 'Florida Blue', ['medical'])
    [item] = job.result['items']
    assert (item['plan'], item['matched']) == (current.id, 'attached')
    values = {value['key']: value for value in item['values']}
    assert set(values) == {'deductible_family', 'pcp_copay', 'specialist_copay'}  # no rate, nothing equal
    assert values['pcp_copay']['old'] == '30' and values['pcp_copay']['low']  # the SBC disagrees: flagged
    assert Plan.objects.get(pk=current.id).values == before
    assert Activity.objects.filter(deal=deal).count() == rows + 1  # the upload only

    ai.apply(job.created_by, job.id)
    plan = Plan.objects.get(pk=current.id)
    assert plan.values['pcp_copay'] == '35' and open_warning(plan.sources['pcp_copay'])
    assert plan.values['deductible_family'] == '5000' and not open_warning(plan.sources['deductible_family'])


def test_D38_attach_sbc_is_refused_in_words_on_a_line_or_plan_it_does_not_fit(admin_api, landed, fake_claude):
    deal, current = landed
    copy = admin_api.post(f'/api/plans/{current.id}/copy/', {'name': 'BlueOptions copy'}, format='json').json()
    answered = admin_api.post(f'/api/plans/{copy["id"]}/sbc/', {'document_id': 1}, format='json')
    assert (
        answered.status_code == 409 and 'takes its design from the plan it was made from' in answered.json()['detail']
    )
    answered = admin_api.post(f'/api/plans/{current.id}/sbc/', {}, format='json')
    assert answered.status_code == 400
    answered = admin_api.post(f'/api/plans/{current.id}/sbc/', {'document_id': 'x'}, format='json')
    assert answered.status_code == 400
