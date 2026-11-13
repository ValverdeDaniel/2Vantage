"""The Overview's "Double-check with AI" (plan.md §10.4, §8.6; M92, M93; D-119; slice 64): one `recheck` reader, shared
with the per-flag re-check, over every plan value read from a file that no person approved — open warnings first, at
most `MAX_PER_FILE` a file — never a laser; agreements arrive ticked and nothing clears until a person applies it.
The fake client answers; every file and figure is synthetic."""

from unittest import mock

import pytest

from ai import services as ai
from ai.services.rechecks import NOTHING_SCANNED
from deals.activity import Refused
from documents.review_rules import is_approved, open_warning
from quotes import recheck, services
from quotes.models import Plan
from quotes.services import review
from quotes.tests.review_world import add_file, read_into, world
from quotes.tests.sbc_world import file_hash

pytestmark = pytest.mark.django_db


def refs(found):
    return [claim['ref'] for claim in found]


def test_M93_scanned_takes_unapproved_values_open_warnings_first_never_a_laser(user):
    w = world(user)
    cigna, uhc = w['cigna'], w['uhc']
    review.mark_values(user, w['deal'], 'approve', refs=[f'plan:{cigna.id}:network'])
    stop = services.create_plan(user, w['deal'], line='stop_loss', role='alternate', carrier='Sun Life', name='Spec')
    read_into(stop, {'sl_lasers': 'ID-1 $90,000', 'sl_spec_deductible': '50000'}, w['doc'], low=('sl_lasers',))
    found = refs(recheck.claims(w['deal'], {'scanned': True}))
    flagged = [f'plan:{cigna.id}:rate_ee', f'plan:{cigna.id}:rate_fam', f'plan:{uhc.id}:rate_ee']
    assert sorted(found[:3]) == sorted(flagged)  # the open warnings first
    assert f'plan:{cigna.id}:network' not in found  # a person approved it
    assert f'plan:{stop.id}:sl_spec_deductible' in found
    assert not any(ref.endswith(':sl_lasers') for ref in found)  # member data never goes to Claude (§3.8)
    assert not any(ref.endswith(':sl_lasers') for ref in refs(recheck.claims(w['deal'], {})))
    with mock.patch.object(recheck, 'MAX_PER_FILE', 2):
        assert refs(recheck.claims(w['deal'], {'scanned': True})) == found[:2]
    assert f'plan:{w["current"].id}:rate_ee' not in found  # typed, no file: nothing to re-read


def test_M92_double_check_waits_for_a_person_and_says_when_nothing_was_scanned(user, admin_user, fake_claude):
    w = world(user)
    other = add_file(user, w['deal'], name='second (synthetic).pdf')
    found = recheck.claims(w['deal'], {'scanned': True})
    checks = [
        {'ref': claim['ref'], 'verdict': 'agree', 'found_value': '', 'page': 1, 'confidence': 'high', 'note': ''}
        for claim in found
    ]
    fake_claude.record(('recheck', file_hash(w['doc']), 'p1#1'), {'checks': checks})
    job, created = ai.start_recheck(admin_user, w['deal'], scanned=True)
    job.refresh_from_db()
    assert created and job.params['scanned'] and job.params['refs'] == refs(found)
    assert job.result['counts']['approvals'] == len(found) and job.result['counts']['fixes'] == 0
    cigna = Plan.objects.get(pk=w['cigna'].id)
    assert open_warning(cigna.sources['rate_ee']) and not is_approved(cigna.sources['network'])  # not before Apply
    ai.apply(user, job.id)
    assert is_approved(Plan.objects.get(pk=w['cigna'].id).sources['network'])
    with pytest.raises(Refused) as refused:  # every value from a file is approved now
        ai.start_recheck(admin_user, w['deal'], scanned=True, document_ids=[other.id])
    assert refused.value.sentence == NOTHING_SCANNED
