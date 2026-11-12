"""Using a quote read and taking it back, on GD3's renewal packet (plan.md §10.5, §13.7 row 19 "done when"; Q.9 row 19;
D60, D61, D67, D72–D75, D117, OQ30). The read is replayed by the fake client; each test builds its own GD3."""

import copy
import hashlib
from types import SimpleNamespace

import pytest

from ai import services as ai
from ai.services.landing import UndoRefused
from deals import activity
from deals.models import Activity, Deal
from documents.models import Document
from quotes import flags
from quotes import services as plans
from quotes.models import LineEnrollment, Plan
from quotes.selectors import comparison

pytestmark = pytest.mark.django_db

D, F = 'BlueOptions PPO 2500', 'BlueCare HMO 1500'


@pytest.fixture
def packet(quote_first, gd3_packet_answer, fake_claude):
    deal = quote_first.built.deal
    document = Document.objects.get(deal=deal, kind='renewal')
    with document.file.open('rb') as handle:
        raw = handle.read()
    answer, label = gd3_packet_answer
    key = ('quotes', hashlib.sha256(raw).hexdigest()[:16], label)
    fake_claude.record(key, answer)
    return SimpleNamespace(deal=deal, document=document, answer=answer, key=key, fake=fake_claude, qf=quote_first)


def read(user, packet, answer=None):
    if answer is not None:
        packet.fake.record(packet.key, answer)
    job, _created = ai.start_read(user, packet.deal, [packet.document.id])
    job.refresh_from_db()
    return job


def ids_of(job, *ops):
    return [item['id'] for item in job.result['items'] if item['op'] in ops]


def made(landed):
    """The plans the read made, in the order it made them: the file's reading order (F138)."""
    return list(Plan.all_objects.filter(id__in=landed['created']).order_by('id'))


def printed(answer, key, col, value):
    """The packet's answer with one printed cell changed (a carrier's corrected figure)."""
    answer = copy.deepcopy(answer)
    row = next(row for row in answer['lines'][0]['rows'] if row['key'] == key)
    next(cell for cell in row['cells'] if cell['col'] == col)['value'] = value
    return answer


def snapshot(deal):
    plans_now = sorted(
        Plan.all_objects.filter(deal=deal).values_list(
            'id', 'role', 'values', 'sources', 'enrollment', 'removed_at', 'updated_at'
        )
    )
    lines = sorted(LineEnrollment.objects.filter(deal=deal).values_list('line', 'enrollment', 'typed_at', 'on'))
    stage = Deal.objects.values_list('stage', flat=True).get(pk=deal.pk)
    return plans_now, lines, Activity.objects.filter(deal=deal).count(), stage


def priced(deal, name):
    row = next(r for r in comparison(deal, 'medical')['plans'] if r['name'] == name and r['role'] == 'current')
    return row['premium']['monthly'], row['enrollment_source']


def test_D72_D75_use_this_scan_lands_gd3_packet_in_printed_order_and_moves_the_deal_to_quoting(user, packet):
    job = read(user, packet)
    assert Deal.objects.get(pk=packet.deal.pk).stage != 'quoting'

    job, landed = ai.apply(user, job.id)

    plans_made = made(landed)
    assert [(plan.role, plan.name) for plan in plans_made] == [
        ('current', D),
        ('renewal', D),
        ('current', F),
        ('renewal', F),
    ]
    assert plans_made[1].renews_id == plans_made[0].id and plans_made[3].renews_id == plans_made[2].id
    board = [row['id'] for row in comparison(packet.deal, 'medical')['plans']]
    new = {plan.id for plan in plans_made}
    assert [pid for pid in board if pid in new] == [plans_made[i].id for i in (0, 2, 1, 3)]  # currents, then renewals
    rate = plans_made[1].sources['rate_ee']
    assert plans_made[1].values['rate_ee'] == '761.4'
    assert (rate['origin'], rate['doc'], rate['page'], rate['read_value']) == ('ai', packet.document.id, 2, '761.4')
    assert rate['loc']['state'] in ('found', 'derived', 'weak')
    assert all(plan.read_ref['job'] == job.id and plan.source_document_id == packet.document.id for plan in plans_made)
    assert not any(plan.enrollment for plan in plans_made)  # printed counts are never a plan's own until ticked (D67)
    assert Deal.objects.get(pk=packet.deal.pk).stage == 'quoting'
    row = Activity.objects.get(pk=landed['activity_id'])
    assert (row.area, landed['activity_ids'], job.activity_id, job.resolution) == (
        'quote_read',
        [row.id],
        row.id,
        'applied',
    )
    assert row.summary == 'Used Claude’s read: 2 current plans · 2 renewals'
    assert flags.rebuild([packet.deal.id]) == []  # the stored counts of open warnings hold (Q.3 #9)


def test_D67_OQ30_accepting_the_printed_counts_prices_both_current_plans(user, packet, golden_keys):
    job = read(user, packet)
    _job, landed = ai.apply(user, job.id, select=ids_of(job, 'create_plan', 'summary_counts'))

    split = golden_keys['GD3']['checkpoints']['A_split']['plans']
    assert priced(packet.deal, D) == (split['D']['monthly'], 'typed')
    assert priced(packet.deal, F) == (split['F']['monthly'], 'typed')
    current = {plan.name: plan.enrollment for plan in made(landed) if plan.role == 'current'}
    assert current == {D: split['D']['enrollment'], F: split['F']['enrollment']}
    areas = list(Activity.objects.filter(pk__in=landed['activity_ids']).order_by('id').values_list('area', flat=True))
    assert areas == ['quote_read', 'enrollment']  # the counts through set_enrollment, the one writer of typed counts


def test_D73_undo_this_run_removes_the_plans_and_their_counts(user, packet):
    job = read(user, packet)
    before = snapshot(packet.deal)
    prices_before = {row['id']: row['premium']['monthly'] for row in comparison(packet.deal, 'medical')['plans']}
    job, landed = ai.apply(user, job.id, select=ids_of(job, 'create_plan', 'summary_counts'))

    job, changed = ai.undo(user, job.id)

    assert changed and job.resolution == 'undone'
    assert not Plan.objects.filter(id__in=landed['created']).exists()
    assert all(plan.removed_at for plan in made(landed))
    after = snapshot(packet.deal)
    assert after[1] == before[1]  # the line's counts, switch and typed_at as they were
    assert after[3] == 'quoting'  # the stage moves only forward (D75)
    assert {
        row['id']: row['premium']['monthly'] for row in comparison(packet.deal, 'medical')['plans']
    } == prices_before
    assert job.result['landed']['undone']['kept'] == []
    assert flags.rebuild([packet.deal.id]) == []
    assert ai.undo(user, job.id)[1] is False  # once


def test_D73_undo_keeps_a_plan_someone_typed_into(user, packet):
    job = read(user, packet)
    job, landed = ai.apply(user, job.id)
    renewal = made(landed)[1]
    plans.update_plan(user, renewal.id, {'values': {'pcp_copay': '35'}})

    job, _changed = ai.undo(user, job.id)

    renewal.refresh_from_db()
    assert renewal.removed_at is None and renewal.role == 'alternate'  # its current plan came off (§5.4)
    assert job.result['landed']['undone']['kept'] == [f'Florida Blue {D}']
    assert Plan.objects.filter(id__in=landed['created']).count() == 1


def test_D73_undo_refuses_after_a_later_edit_and_undo_anyway_leaves_it(user, packet):
    first = read(user, packet)
    _first, landed = ai.apply(user, first.id)
    renewal = made(landed)[1]
    corrected = printed(printed(packet.answer, 'rate_ee', 2, '$771.40'), 'rate_es', 2, '$1,600.00')
    second = read(user, packet, corrected)
    (fills,) = [item for item in second.result['items'] if item.get('plan') == renewal.id]
    assert {value['key'] for value in fills['values'] if value['tick']} == {'rate_ee', 'rate_es'}  # Claude's own
    ai.apply(user, second.id)
    plans.update_plan(user, renewal.id, {'values': {'rate_ee': '780'}})

    with pytest.raises(UndoRefused) as refused:
        ai.undo(user, second.id)
    assert refused.value.keys == ['rate_ee'] and 'changed after this' in refused.value.sentence
    job, _changed = ai.undo(user, second.id, force=True)

    renewal.refresh_from_db()
    assert job.resolution == 'undone' and renewal.values['rate_ee'] == '780'
    back = renewal.sources['rate_es']
    assert renewal.values['rate_es'] == '1598.85'  # back as the first read had it, with its file (F141)
    assert (back['origin'], back['read_value'], back['doc']) == ('ai', '1598.85', packet.document.id)


def test_D60_an_unchanged_re_read_writes_nothing(user, packet):
    first = read(user, packet)
    ai.apply(user, first.id, select=ids_of(first, 'create_plan', 'summary_counts'))
    before = snapshot(packet.deal)

    again = read(user, packet)
    assert not any(item['tick'] for item in again.result['items'])
    assert not ids_of(again, 'create_plan', 'summary_counts')  # every plan matched; the counts are held
    job, landed = ai.apply(user, again.id)

    assert snapshot(packet.deal) == before
    assert (landed['activity_ids'], job.activity_id, job.resolution) == ([], None, 'applied')


def test_D61_typed_values_stay_untouched_unless_the_person_ticks_them(user, packet):
    first = read(user, packet)
    _first, landed = ai.apply(user, first.id)
    current = made(landed)[0]
    plans.update_plan(user, current.id, {'values': {'rate_ee': '700.00'}})
    again = read(user, packet)
    (item,) = [item for item in again.result['items'] if item.get('plan') == current.id]
    (value,) = item['values']
    assert (value['key'], value['tick'], value['why']) == ('rate_ee', False, 'Typed by a person')

    ai.apply(user, again.id)  # Use this scan: the read as proposed
    current.refresh_from_db()
    assert (current.values['rate_ee'], current.sources['rate_ee']['origin']) == ('700', 'typed')

    third = read(user, packet)
    (item,) = [item for item in third.result['items'] if item.get('plan') == current.id]
    ai.apply(user, third.id, select=[item['id'], f'{item["id"]}:rate_ee'])  # Apply 1 selected, the value ticked
    current.refresh_from_db()
    assert (current.values['rate_ee'], current.sources['rate_ee']['origin']) == ('702.4', 'ai')


def test_D117_a_current_plan_the_deal_has_is_matched_and_the_other_is_placed_by_the_person(user, packet):
    built = packet.qf.arrive('D').built
    job = read(user, packet)
    by_op = {item['op']: item for item in job.result['items'] if item.get('role') == 'current'}
    assert by_op['set_values']['plan'] == built.refs['D']
    pick = by_op['pick_current']
    assert pick['tick'] is False and [option['plan'] for option in pick['options']] == [built.refs['D']]

    _job, landed = ai.apply(
        user, job.id, select=ids_of(job, 'create_plan', 'set_values', 'pick_current'), picks={pick['id']: 'new'}
    )

    currents = Plan.objects.filter(deal=packet.deal, line='medical', role='current').order_by('sort_order')
    assert [plan.name for plan in currents] == [D, F]  # never a second BlueOptions (D117)
    renewals = {plan.renews.name: plan for plan in Plan.objects.filter(deal=packet.deal, role='renewal')}
    assert set(renewals) == {D, F} and renewals[D].renews_id == built.refs['D']


def test_D73_the_change_history_revert_of_a_landing_takes_the_plans_off(user, packet):
    job = read(user, packet)
    _job, landed = ai.apply(user, job.id)
    activity.revert(landed['activity_id'], user)
    assert not Plan.objects.filter(id__in=landed['created']).exists()
    with pytest.raises(activity.Refused):
        activity.revert(landed['activity_id'], user)


def test_D72_a_read_is_used_once(user, packet):
    job = read(user, packet)
    ai.apply(user, job.id)
    with pytest.raises(activity.Refused):
        ai.apply(user, job.id)
    with pytest.raises(activity.Refused):
        ai.discard(user, job.id)
