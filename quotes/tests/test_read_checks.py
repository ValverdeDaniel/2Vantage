"""The checks on what Claude proposes (plan.md §10.4; D88, D76; the old plan_checks.verify): hard findings step a read
up to Opus 5.5 for an admin, soft ones are only listed. Pure checks on change-set items, then GD3's packet read."""

import copy
import hashlib

from ai import pricing
from ai import services as ai_services
from quotes import read_checks

LOC_ABSENT = {'state': 'absent'}


def plan_item(item_id, role, values=(), codes=(), op='create_plan', renews=None, line='medical'):
    return {
        'id': item_id,
        'op': op,
        'plan': None,
        'line': line,
        'role': role,
        'carrier': 'Example Health',
        'name': f'Plan {item_id}',
        'codes': list(codes),
        'renews': renews,
        'values': [{'key': key, 'new': value, 'loc': loc} for key, value, loc in values],
    }


RATES = (('rate_ee', '500', {}), ('rate_es', '1000', {}), ('rate_ec', '900', {}), ('rate_fam', '1500', {}))


def kinds(findings):
    return sorted((finding['kind'], finding['hard']) for finding in findings)


def test_D88_hard_findings_are_facts_code_is_sure_of():
    items = [
        plan_item('i1', 'current', RATES, codes=['108114-00']),
        plan_item('i2', 'alternate', [('rate_ee', '400', LOC_ABSENT)], codes=['108114-00']),
        plan_item('i3', 'alternate', codes=['77001-01']),
        plan_item('i4', 'current', RATES),
        plan_item('i5', 'renewal', RATES, renews={'item': 'i1'}),
    ]
    found = kinds(read_checks.for_read(items, {}))
    assert ('absent_rate', True) in found  # a rate printed nowhere in its file
    assert ('no_rates', True) in found  # i3 comes with no rates on a tier-rated line
    assert ('unpaired', True) in found  # i4 has no renewal on a line with renewals
    assert ('shared_code', True) not in found  # i1 and i2 share a code but not a role
    items[1]['role'] = 'current'
    assert ('shared_code', True) in kinds(read_checks.for_read(items, {}))


def test_D88_soft_findings_are_only_listed():
    bad_order = (('rate_ee', '900', {}), ('rate_es', '800', {}), ('rate_fam', '700', {}))
    items = [
        plan_item('i1', 'alternate', (*bad_order, ('deductible_single', '1000', {'state': 'absent'}))),
        plan_item('i2', 'alternate', (*RATES, ('group_premium_monthly', '9999', {}))),
        {'id': 'i3', 'op': 'summary_counts', 'for': {'item': 'i2'}, 'counts': {'EE': 2, 'ES': 1}},
    ]
    found = read_checks.for_read(items, {})
    assert not any(finding['hard'] for finding in found)
    assert ('tier_order', False) in kinds(found) and ('absent', False) in kinds(found)
    premium = next(finding for finding in found if finding['kind'] == 'premium')
    assert '$2,000 a month' in premium['text'] and '$9,999' in premium['text']  # 2 × 500 + 1 × 1000


def _record(fake, document, answer, label):
    with document.file.open('rb') as handle:
        raw = handle.read()
    fake.record(('quotes', hashlib.sha256(raw).hexdigest()[:16], label), answer)


def test_D88_D76_gd3_packet_reads_clean_and_an_unpaired_current_plan_steps_an_admins_read_up(
    gd3, gd3_packet, user, admin_user, fake_claude
):
    document, answer, label = gd3_packet
    _record(fake_claude, document, answer, label)
    job, _ = ai_services.start_read(user, gd3.deal, [document.id])
    job.refresh_from_db()
    assert not any(finding['hard'] for finding in job.result['findings'])  # the perfect read raises nothing hard

    unpaired = copy.deepcopy(answer)
    renewal = next(col for col in unpaired['lines'][0]['columns'] if col['side'] == 'renewal')
    renewal['side'], renewal['renews_col'] = 'quote', -1
    _record(fake_claude, document, unpaired, label)
    fake_claude.log.clear()
    job, _ = ai_services.start_read(admin_user, gd3.deal, [document.id], review=True)
    job.refresh_from_db()
    assert any(finding['kind'] == 'unpaired' for finding in job.result['findings'])
    assert [entry['params']['model'] for entry in fake_claude.log] == [pricing.SONNET, pricing.OPUS]
