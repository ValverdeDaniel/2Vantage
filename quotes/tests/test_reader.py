"""The quote reader's change set (plan.md §10.4, §10.5; D56–D62, D115–D117, F138, F143, E93, OQ30; slice 18), read
with the fake client from the synthetic corpus. Nothing a read stages is written: these check what it proposes."""

import hashlib

from ai import services as ai_services
from conftest import make_deal
from documents.tests.helpers import stored
from quotes import services as plans
from quotes.reader import corpus, faults, merge, rules
from quotes.reader.schema import NO_RENEWAL


def read(user, deal, fake, case, answer=None, kind=None):
    document = stored(
        user,
        deal,
        case.filename,
        case.raw,
        kind=kind or case.kind,
        role=case.role,
        carrier=case.carrier,
        lines=case.lines,
    )
    fake.record(('quotes', hashlib.sha256(case.raw).hexdigest()[:16], case.range), answer or case.answer)
    job, _ = ai_services.start_read(user, deal, [document.id])
    job.refresh_from_db()
    return job.result, document


def by_op(result, op):
    return [item for item in result['items'] if item['op'] == op]


def values_of(item):
    return {value['key']: value for value in item['values']}


def test_F138_D62_new_plans_come_in_the_file_s_column_order(user, deal, fake_claude):
    result, _ = read(user, deal, fake_claude, corpus.quotes_three())
    assert [item['name'] for item in by_op(result, 'create_plan')] == [
        'Harbor Open PPO 1500',
        'Harbor Open EPO 2500',
        'Harbor HSA 3500',
    ]
    assert all(item['role'] == 'alternate' for item in by_op(result, 'create_plan'))


def test_F143_D58_codes_and_house_formats_ride_on_each_plan(user, deal, fake_claude):
    result, _ = read(user, deal, fake_claude, corpus.renewal_two_current())
    current = by_op(result, 'create_plan')[0]
    assert current['codes'] == ['CH-104455', 'CP2000'] and current['plan_number'] == 'CP2000'
    assert values_of(current)['deductible_single']['new'] == '2000'  # "$2000 / $4000": the pair split (D54)
    assert values_of(current)['deductible_family']['new'] == '4000'
    assert values_of(current)['rate_ee']['new'] == '688.4'


def test_D58_a_starred_rate_is_a_finding_and_never_a_value(user, deal, fake_claude):
    case = corpus.quotes_three()
    result, _ = read(user, deal, fake_claude, case, answer=faults.faulty(case, 'starred_rate'))
    first = by_op(result, 'create_plan')[0]
    assert 'rate_ee' not in values_of(first)
    assert any('$712.35*' in finding['text'] for finding in result['findings'])


def test_D61_typed_values_are_left_alone_and_claudes_own_are_replaced(user, deal, fake_claude):
    plans.create_plan(
        user,
        deal,
        line='medical',
        role='alternate',
        carrier='Harbor Mutual (synthetic)',
        name='Harbor Open PPO 1500',
        plan_number='HM-PPO-1500',
        values={'rate_ee': '700'},
    )
    plan = plans.create_plan(
        user,
        deal,
        line='medical',
        role='alternate',
        carrier='Harbor Mutual (synthetic)',
        name='Harbor Open EPO 2500',
        plan_number='HM-EPO-2500',
        values={'rate_ee': '650', 'pcp_copay': '30'},
        source_origin='ai',
    )
    result, _ = read(user, deal, fake_claude, corpus.quotes_three())
    typed, read_before = by_op(result, 'set_values')
    assert (typed['matched'], read_before['plan']) == ('number', plan.id)
    assert values_of(typed)['rate_ee']['tick'] is False and values_of(typed)['rate_ee']['why'] == 'Typed by a person'
    assert values_of(read_before)['rate_ee'] == {**values_of(read_before)['rate_ee'], 'old': '650', 'tick': True}
    assert 'pcp_copay' not in values_of(read_before)  # equal: nothing to write (D60)


def test_D117_a_current_plan_is_never_duplicated_it_asks_which_it_is(user, deal, fake_claude):
    held = plans.create_plan(user, deal, line='medical', role='current', carrier='Other Carrier', name='Old Plan')
    result, _ = read(user, deal, fake_claude, corpus.renewal_two_current())
    picks = by_op(result, 'pick_current')
    assert len(picks) == 2 and all(not item['tick'] for item in picks)
    assert picks[0]['options'] == [{'plan': held.id, 'label': 'Other Carrier Old Plan'}]
    assert not [item for item in by_op(result, 'create_plan') if item['role'] == 'current']


def test_D116_a_plan_under_two_numbers_matches_either_half(user, deal, fake_claude):
    held = plans.create_plan(
        user,
        deal,
        line='medical',
        role='current',
        carrier='Gulfside Blue (synthetic)',
        name='Options PPO',
        plan_number='05183',
    )
    result, _ = read(user, deal, fake_claude, corpus.pair_two_numbers())
    (item,) = by_op(result, 'set_values')
    assert (item['plan'], item['matched']) == (held.id, 'number')


def test_D117_a_renewal_whose_link_was_missed_is_read_as_an_alternate(user, deal, fake_claude):
    case = corpus.renewal_two_current()
    result, _ = read(user, deal, fake_claude, case, answer=faults.faulty(case, 'missed_link'))
    roles = [item['role'] for item in by_op(result, 'create_plan')]
    assert roles == ['current', 'alternate', 'current', 'alternate']


def test_OQ30_printed_counts_are_not_proposed_over_a_census(quote_first, gd3_packet_answer, fake_claude):
    answer, label = gd3_packet_answer
    built = quote_first.census().built
    from documents.models import Document

    document = Document.objects.get(deal=built.deal, kind='renewal')
    with document.file.open('rb') as handle:
        fake_claude.record(('quotes', hashlib.sha256(handle.read()).hexdigest()[:16], label), answer)
    job, _ = ai_services.start_read(quote_first.user, built.deal, [document.id])
    job.refresh_from_db()
    assert not by_op(job.result, 'summary_counts')
    assert any('census already prices' in finding['text'] for finding in job.result['findings'])


def test_D56_lines_the_deal_does_not_ask_for_become_one_add_lines_item(user, fake_claude):
    asked = make_deal(user, name='Dental only Co.', requested_lines=('dental',))
    result, _ = read(user, asked, fake_claude, corpus.quotes_three())
    (item,) = by_op(result, 'add_lines')
    assert (item['lines'], item['tick']) == (['medical'], False)
    nothing = make_deal(user, name='No lines Co.', requested_lines=())
    result, _ = read(user, nothing, fake_claude, corpus.quotes_three())
    assert by_op(result, 'add_lines')[0]['tick'] is True


def test_D66_unmapped_rows_keep_their_printed_text_except_in_member_files(user, deal, fake_claude):
    result, _ = read(user, deal, fake_claude, corpus.quotes_three())
    (layout,) = result['layout']
    chiro = next(row for row in layout['rows'] if row['label'] == 'Chiropractic visits')
    assert chiro['keys'] == [] and set(chiro['printed'].values()) == {'20 a year'}
    assert layout['columns'] == [item['id'] for item in by_op(result, 'create_plan')]
    other = make_deal(user, name='Stop-loss Co.')
    result, _ = read(user, other, fake_claude, corpus.quotes_three(), kind='stop_loss_quote')
    assert all(row['printed'] == {} for row in result['layout'][0]['rows'])


def test_E93_a_printed_label_with_a_person_s_details_is_never_kept():
    assert rules.printed_line('Employee only') == 'Employee only'
    assert rules.printed_line('Jane Tester DOB 01/02/1970 SSN 123-45-6789') == ''


def test_D60_an_unchanged_reread_proposes_no_value(user, deal, fake_claude):
    case = corpus.quotes_three()
    first, _ = read(user, deal, fake_claude, case)
    for item in by_op(first, 'create_plan'):
        plans.create_plan(
            user,
            deal,
            line=item['line'],
            role=item['role'],
            carrier=item['carrier'],
            name=item['name'],
            plan_number=item['plan_number'],
            source_origin='ai',
            values={value['key']: value['new'] for value in item['values']},
        )
    again, _ = read(user, deal, fake_claude, case)
    assert all(
        item['op'] == 'set_values' and item['values'] == [] and not item['tick'] for item in by_op(again, 'set_values')
    )
    assert not by_op(again, 'create_plan')


def test_D57_a_plan_on_two_pages_is_one_plan_and_a_later_file_wins():
    from ai.ranges import Range
    from ai.read_files import FileIn

    older, newer = FileIn(id=1, raw=b'', extension='.pdf', order=0), FileIn(id=2, raw=b'', extension='.pdf', order=1)
    column = {
        'col': 1,
        'carrier': 'Acme',
        'plan_name': 'Gold 1500',
        'plan_number': '',
        'codes': [],
        'side': 'quote',
        'renews_col': NO_RENEWAL,
        'replaces': '',
        'unsure': False,
    }

    def block(key, value, page):
        return {
            'lines': [
                {
                    'line': 'medical',
                    'columns': [column],
                    'counts': [],
                    'rows': [
                        {
                            'label': key,
                            'key': key,
                            'cells': [{'col': 1, 'value': value, 'page': page, 'cell': '', 'unsure': False}],
                        }
                    ],
                }
            ]
        }

    joined = merge.merge(
        [
            (older, Range('pdf', pages=(1,)), block('deductible_single', '1500', 1)),
            (older, Range('pdf', pages=(2,)), block('rate_ee', '512.34', 2)),
            (newer, Range('pdf', pages=(1,)), block('rate_ee', '520.00', 1)),
        ],
        [older, newer],
    )
    (plan,) = joined['plans']
    assert set(plan['values']) == {'deductible_single', 'rate_ee'} and plan['docs'] == [1, 2]
    assert plan['values']['rate_ee']['value'] == '520.00' and joined['conflicts'][0]['other'] == '512.34'
