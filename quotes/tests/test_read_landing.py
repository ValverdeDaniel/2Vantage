"""Who lands GD3's renewal packet (plan.md §10.1, §13.7 row 20 "done when"; Q.9 row 20: landing by person, lock and
lost deal; D71, D73, E75): an admin's read lands at once with ↶ Undo this run, a producer's waits for review and writes
nothing. The read is replayed by the fake client; each test builds its own GD3."""

import hashlib

import pytest
from django.utils import timezone

from ai import land
from ai import services as ai
from ai.models import DealAi
from deals import rules
from deals.models import Activity, Deal
from documents.models import Document
from quotes.models import Plan

pytestmark = pytest.mark.django_db


@pytest.fixture
def packet(quote_first, gd3_packet_answer, fake_claude):
    deal = quote_first.built.deal
    document = Document.objects.get(deal=deal, kind='renewal')
    with document.file.open('rb') as handle:
        raw = handle.read()
    answer, label = gd3_packet_answer
    fake_claude.record(('quotes', hashlib.sha256(raw).hexdigest()[:16], label), answer)
    return deal, document


def state(deal):
    plans = sorted(Plan.all_objects.filter(deal=deal).values_list('id', 'role', 'values', 'removed_at'))
    return plans, Activity.objects.filter(deal=deal).count(), Deal.objects.get(pk=deal.pk).stage


def read(person, deal, document, **options):
    job, _created = ai.start_read(person, deal, [document.id], **options)
    job.refresh_from_db()
    return job


def test_D71_D73_an_admins_read_of_the_packet_lands_at_once_and_undo_takes_it_back(admin_user, packet):
    deal, document = packet
    before = state(deal)
    job = read(admin_user, deal, document)
    assert (job.land, job.resolution) == (land.AUTO, 'applied')
    made = Plan.objects.filter(id__in=job.result['landed']['created'])
    assert sorted(made.values_list('role', flat=True)) == ['current', 'current', 'renewal', 'renewal']
    assert Deal.objects.get(pk=deal.pk).stage == 'quoting'  # the first landed quote read moves it (D75)
    assert set(job.result['landed']['plan_ids']) >= set(job.result['landed']['created'])  # what the board flashes
    ai.undo(admin_user, job.id)
    plans, _rows, _stage = state(deal)
    assert [plan for plan in plans if plan[3] is None] == [plan for plan in before[0] if plan[3] is None]


def test_D71_a_producers_read_waits_for_review_and_writes_nothing(user, packet):
    deal, document = packet
    before = state(deal)
    job = read(user, deal, document)
    assert (job.land, job.resolution, job.wait_reason) == (land.STAGED, '', land.WAITS)
    assert state(deal) == before


@pytest.mark.parametrize('why', ['lost', 'locked', 'reread'])
def test_D71_D104_E75_a_lost_deal_a_locked_table_or_a_reread_keeps_an_admins_read_waiting(admin_user, packet, why):
    deal, document = packet
    options = {}
    if why == 'lost':
        Deal.objects.filter(pk=deal.pk).update(stage='lost')
    elif why == 'locked':
        DealAi.objects.create(deal=deal, locked_by=admin_user, locked_at=timezone.now())
    else:
        options['review'] = True
    before = state(deal)
    job = read(admin_user, deal, document, **options)
    said = {'lost': rules.REFUSALS['ai_land'], 'locked': land.LOCKED, 'reread': land.ASKED}[why]
    assert (job.land, job.wait_reason) == (land.STAGED, said)
    assert state(deal) == before
