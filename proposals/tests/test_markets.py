"""Markets checked (plan.md §8.14; J63, K117; Q.9 row 26 "`asked_by_line` with no sends"). Pure: the rows from the
lines' plans, who the RFP asked (`rfp.asked_by_line`'s shape) and the producer's choices."""

from proposals import markets


def plan(carrier, *, current=False, shown=True, name='Plan'):
    return {'carrier': carrier, 'name': name, 'current': current, 'shown': shown}


def medical(*plans, incumbent=''):
    return {'key': 'medical', 'label': 'Medical', 'plans': list(plans), 'incumbent': incumbent, 'renewal_note': ''}


def settings(on=None, **lines):
    return {'on': on, 'lines': lines}


def rows_of(found, key='medical'):
    entry = next(line for line in found['lines'] if line['key'] == key)
    return [(row['carrier'], row['current'], row['quoted'], row['presented']) for row in entry['rows']]


LINE = medical(
    plan('Aetna', current=True),
    plan('Aetna'),  # the incumbent's renewal: still the incumbent's row
    plan('Cigna'),
    plan('UHC', shown=False),
    plan('Cigna Dual'),  # one carrier, one row
)


def test_J63_with_no_rfp_sent_the_quoting_carriers_are_listed_and_the_table_waits():
    found = markets.marketing([LINE], {}, settings())
    assert rows_of(found) == [
        ('Aetna', True, None, True),
        ('Cigna', False, True, True),
        ('UnitedHealthcare', False, True, False),
    ]
    assert found['has_asks'] is False and found['auto'] is False and found['on'] is False


def test_J63_a_carrier_asked_who_did_not_quote_reads_no_and_the_table_shows_itself():
    asked = {
        'medical': [{'id': 'cigna', 'name': 'Cigna', 'on': '2026-10-01'}, {'id': 'aetna', 'name': 'Aetna', 'on': ''}]
    }
    asked['medical'].append({'id': 'curative', 'name': 'Curative', 'on': '2026-10-01'})
    found = markets.marketing([LINE], asked, settings())
    assert rows_of(found)[-1] == ('Curative', False, False, False)
    assert found['has_asks'] and found['auto'] and found['on']
    cigna = next(row for row in found['lines'][0]['rows'] if row['id'] == 'cigna')
    assert (
        cigna['asked']
        and not next(row for row in found['lines'][0]['rows'] if row['id'] == 'unitedhealthcare')['asked']
    )


def test_J63_an_unregistered_asked_carrier_merges_with_its_quote_and_unmatched_names_are_listed():
    vision = {
        'key': 'vision',
        'label': 'Vision',
        'plans': [plan('VSP Vision Care Inc.', current=True), plan('EyeMed Vision'), plan('', name='Mystery')],
        'incumbent': '',
        'renewal_note': '',
    }
    asked = {'vision': [{'id': 'n:vsp', 'name': 'VSP', 'on': ''}, {'id': 'n:davis', 'name': 'Davis', 'on': ''}]}
    found = markets.marketing([vision], asked, settings())
    entry = found['lines'][0]
    assert [row['carrier'] for row in entry['rows']] == ['VSP Vision Care Inc.', 'EyeMed Vision', 'Davis']
    assert entry['rows'][0]['asked'] and entry['rows'][2]['quoted'] is False
    assert entry['unmatched'] == ['EyeMed Vision', 'Unknown carrier (Mystery)']


def test_J63_a_line_nobody_marketed_is_not_listed_and_notes_hidden_rows_and_show_it_are_the_producers():
    kept = {
        'key': 'dental',
        'label': 'Dental',
        'plans': [plan('Guardian', current=True)],
        'incumbent': '',
        'renewal_note': '',
    }
    choices = settings(on=True, medical=({'cigna': 'Competitive'}, {'unitedhealthcare'}))
    found = markets.marketing([LINE, kept], {}, choices)
    assert [line['key'] for line in found['lines']] == ['medical']
    by_id = {row['id']: row for row in found['lines'][0]['rows']}
    assert by_id['cigna']['note'] == 'Competitive' and by_id['unitedhealthcare']['hidden']
    assert found['override'] is True and found['on'] is True


def test_J63_with_no_current_plan_the_coverage_rows_carrier_is_the_incumbent():
    found = markets.marketing([medical(plan('Cigna'), incumbent='Florida Blue')], {}, settings())
    assert rows_of(found)[0] == ('Florida Blue', True, None, False)
