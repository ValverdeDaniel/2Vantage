"""Slice 18's done-when on GD3 (plan.md §13.7; Q.9 row 18; OQ30): a read of the renewal packet stages the change set —
two current plans and their renewals in printed order, their per-plan printed counts unticked — and writes nothing."""

import hashlib

from ai import services as ai_services
from deals.models import Activity
from quotes.models import LineEnrollment, Plan


def _record(fake, document, answer, label):
    with document.file.open('rb') as handle:
        raw = handle.read()
    fake.record(('quotes', hashlib.sha256(raw).hexdigest()[:16], label), answer)


def _snapshot(deal):
    plans = sorted(Plan.all_objects.filter(deal=deal).values_list('id', 'role', 'values', 'sources', 'enrollment'))
    lines = sorted(LineEnrollment.objects.filter(deal=deal).values_list('line', 'enrollment', 'typed_at'))
    return plans, lines, Activity.objects.filter(deal=deal).count()


def test_F138_D117_OQ30_gd3_packet_stages_current_plans_and_renewals_in_printed_order(
    gd3, gd3_packet, user, fake_claude
):
    document, answer, label = gd3_packet
    _record(fake_claude, document, answer, label)
    before = _snapshot(gd3.deal)

    job, created = ai_services.start_read(user, gd3.deal, [document.id])
    job.refresh_from_db()

    assert created and job.status == 'done' and job.land == 'staged'
    items = job.result['items']
    plans = [item for item in items if item['op'] == 'create_plan']
    assert [(item['role'], item['name']) for item in plans] == [
        ('current', 'BlueOptions PPO 2500'),
        ('renewal', 'BlueOptions PPO 2500'),
        ('current', 'BlueCare HMO 1500'),
        ('renewal', 'BlueCare HMO 1500'),
    ]
    assert plans[1]['renews']['item'] == plans[0]['id'] and plans[3]['renews']['item'] == plans[2]['id']
    assert plans[1]['renews']['label'] == 'Florida Blue BlueOptions PPO 2500'
    assert all(item['carrier'] == 'Florida Blue' for item in plans)
    counts = [item for item in items if item['op'] == 'summary_counts']
    assert [(item['for'], item['counts'], item['tick']) for item in counts] == [
        ({'item': plans[0]['id']}, {'EE': 18, 'ES': 5, 'EC': 4, 'FAM': 5}, False),
        ({'item': plans[2]['id']}, {'EE': 12, 'ES': 3, 'EC': 2, 'FAM': 3}, False),
    ]
    renewal_rates = {value['key']: value['new'] for value in plans[1]['values']}
    assert renewal_rates['rate_ee'] == '761.4' and renewal_rates['rate_fam'] == '2284.2'
    assert _snapshot(gd3.deal) == before  # nothing written: plans, counts, Activity


def test_E79_D95_gd3_packet_values_are_found_in_the_packet_before_review(gd3, gd3_packet, user, fake_claude):
    document, answer, label = gd3_packet
    _record(fake_claude, document, answer, label)
    job, _ = ai_services.start_read(user, gd3.deal, [document.id])
    job.refresh_from_db()
    values = [value for item in job.result['items'] for value in item.get('values') or []]
    assert values and all(value['loc']['state'] in ('found', 'derived', 'weak') for value in values)
    assert all(value['page'] == 2 for value in values)


def test_D49_gd3_packet_header_only_page_is_left_out(gd3, gd3_packet, user, fake_claude):
    document, answer, label = gd3_packet
    _record(fake_claude, document, answer, label)
    job, _ = ai_services.start_read(user, gd3.deal, [document.id])
    job.refresh_from_db()
    assert fake_claude.keys() == [('quotes', fake_claude.keys()[0][1], 'p1-2')]
    assert job.result['left_out_pages'] == [{'doc': document.id, 'pages': [3], 'why': ['header']}]
