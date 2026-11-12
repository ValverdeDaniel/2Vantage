"""✦ Ask Claude to re-check (plan.md §10.4, §13.7 row 22 "done when"; Q.9 row 22 "re-check approvals carry the
person"; D40, D93, E77, F66): flagged values read again against their page; agreements and fixes wait until a person
applies them, approvals carry that person (`via: recheck`), and ↶ Undo this run takes them back. The fake client
answers; every file and figure is synthetic."""

import pytest
from rest_framework.exceptions import ValidationError

from ai import land
from ai import services as ai
from ai.services.rechecks import NOTHING
from deals.activity import Refused
from deals.models import Activity
from documents.review_rules import is_approved, open_warning
from quotes.models import Plan
from quotes.tests.review_world import read_into
from quotes.tests.sbc_world import add_sbc, file_hash, quote_world, read_sbc

pytestmark = pytest.mark.django_db


def verdict(ref, kind, found='', confidence='high', page=1):
    return {'ref': ref, 'verdict': kind, 'found_value': found, 'page': page, 'confidence': confidence, 'note': ''}


@pytest.fixture
def flagged(admin_user, fake_claude):
    """Two flagged values on Cigna's quote, both from its SBC (page 1): the PCP copay the SBC read replaced (it
    disagreed with the quote), and an ER copay Claude doubted."""
    deal, _current, _renewal, cigna = quote_world(admin_user)
    document = add_sbc(admin_user, deal, fake_claude, 'Cigna', 'Open Access 2500', {'pcp_copay': '35'})
    ai.apply(admin_user, read_sbc(admin_user, deal, document).id)
    cigna = read_into(Plan.objects.get(pk=cigna.id), {'er_copay': '250'}, document, low=('er_copay',))
    return deal, document, cigna


def record(fake, document, checks):
    fake.record(('recheck', file_hash(document), 'p1#1'), {'checks': checks})


def test_D93_E77_a_recheck_proposes_and_nothing_changes_until_a_person_applies(user, admin_user, flagged, fake_claude):
    deal, document, cigna = flagged
    pcp, er = f'plan:{cigna.id}:pcp_copay', f'plan:{cigna.id}:er_copay'
    record(fake_claude, document, [verdict(pcp, 'agree'), verdict(er, 'differs', '$275')])
    rows = Activity.objects.filter(deal=deal).count()
    job, created = ai.start_recheck(admin_user, deal, plan_ids=[cigna.id])
    job.refresh_from_db()
    assert created and (job.kind, job.land, job.wait_reason) == ('recheck', land.STAGED, ai.landing.RECHECK_WAITS)
    ops = {item['values'][0]['key']: item for item in job.result['items']}
    assert ops['pcp_copay']['op'] == 'confirm' and ops['pcp_copay']['tick']
    assert (ops['er_copay']['op'], ops['er_copay']['values'][0]['new']) == ('set_values', '275')
    assert Activity.objects.filter(deal=deal).count() == rows  # nothing until a person applies it (D-119)
    plan = Plan.objects.get(pk=cigna.id)
    assert open_warning(plan.sources['pcp_copay']) and plan.values['er_copay'] == '250'

    job, landed = ai.apply(user, job.id)
    plan = Plan.objects.get(pk=cigna.id)
    confirmed = plan.sources['pcp_copay']['confirmed']
    assert (confirmed['by'], confirmed['via']) == (user.id, 'recheck')  # the person who pressed Apply (E77)
    assert plan.values['er_copay'] == '275' and not open_warning(plan.sources['er_copay'])
    assert landed['summary'] == 'approved 1 value · fixed 1 value'

    ai.undo(user, job.id)
    plan = Plan.objects.get(pk=cigna.id)
    assert not is_approved(plan.sources['pcp_copay']) and open_warning(plan.sources['pcp_copay'])
    assert plan.values['er_copay'] == '250' and open_warning(plan.sources['er_copay'])


def test_D93_formatting_is_no_fix_and_not_found_stays_flagged(admin_user, flagged, fake_claude):
    deal, document, cigna = flagged
    pcp, er = f'plan:{cigna.id}:pcp_copay', f'plan:{cigna.id}:er_copay'
    record(fake_claude, document, [verdict(pcp, 'differs', '$35.00'), verdict(er, 'not_found', page=0)])
    job, _created = ai.start_recheck(admin_user, deal, document_ids=[document.id])
    job.refresh_from_db()
    [item] = job.result['items']
    assert (item['op'], item['values'][0]['key']) == ('confirm', 'pcp_copay')
    [missing] = job.result['unverified']
    assert (missing['key'], missing['reason']) == ('er_copay', 'not found on its page')


def test_D93_only_flagged_values_with_a_file_are_rechecked(admin_user, flagged, fake_claude):
    deal, _document, cigna = flagged
    with pytest.raises(Refused) as refused:
        ai.start_recheck(admin_user, deal, refs=[f'plan:{cigna.id}:deductible_single'])
    assert refused.value.sentence == NOTHING
    with pytest.raises(ValidationError):
        ai.start_recheck(admin_user, deal, plan_ids=[cigna.id + 10_000])


def test_E77_a_recheck_with_nothing_to_apply_ends_without_waiting(admin_user, flagged, fake_claude):
    deal, document, cigna = flagged
    checks = [verdict(f'plan:{cigna.id}:{key}', 'not_found', page=0) for key in ('pcp_copay', 'er_copay')]
    record(fake_claude, document, checks)
    job, _created = ai.start_recheck(admin_user, deal, plan_ids=[cigna.id])
    job.refresh_from_db()
    assert job.status == 'done' and not job.result['items'] and len(job.result['unverified']) == 2
    assert not ai.landing.waiting(job)
