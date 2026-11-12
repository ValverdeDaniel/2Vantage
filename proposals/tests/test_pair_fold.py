"""Florida Blue's 05182 and 05183 printed as one column (plan.md §13.8 row 33, "done when"; D-219, J15, F137, OQ42;
Q.9 row 33): the one column's values against the old answer sheet (pure), and on GD1 the pair on Pages, in the PDF,
the PowerPoint and the spreadsheet as one column whose total is the pair's package, counting once and keeping the
first plan's number; Split restores two, and the `split_plan` check asks for the pair until it is made."""

import io
from types import SimpleNamespace

import pytest
from pptx import Presentation
from pypdf import PdfReader

from proposals import line_layout, pair_fold
from proposals.workbook import build as workbook
from quotes import packages as pk
from quotes import selectors
from quotes import services as plans

pytestmark = pytest.mark.django_db

# The two halves as the old answer sheet reads them (plan values, no member data; old plan_merge_tests.HALF_*).
HALF_EE = {
    'deductible_single': '2500',
    'oop_max_single': '5000',
    'deductible_single_oon': '5000',
    'oop_max_single_oon': '10000',
    'rate_ee': '1105.26',
    'coinsurance': '10',
}
HALF_DEP = {
    'deductible_single': '5000',
    'deductible_family': '5000',
    'oop_max_single': '6850',
    'oop_max_family': '10000',
    'deductible_single_oon': '10000',
    'deductible_family_oon': '10000',
    'oop_max_single_oon': '20000',
    'oop_max_family_oon': '20000',
    'rate_es': '2520.00',
    'rate_ec': '2210.52',
    'rate_fam': '3625.26',
    'coinsurance': '10',
}


def _row(pid, name, number, values, **marks):
    shown = {'recommended': False, 'starred': True, 'sold': False, **marks}
    return SimpleNamespace(id=pid, name=name, client_name='', plan_number=number, values=values, **shown)


def test_J15_OQ42_the_one_column_matches_the_old_answer_sheet():
    ee = _row(1, 'BlueOptions HSA Compatible 05182 Non-Embedded', '05182', HALF_EE)
    dep = _row(2, 'BlueOptions HSA Compatible 05183 Non-Embedded', '05183', HALF_DEP)
    column = pair_fold.column(ee, dep)
    assert column.values == {
        'deductible_single': 'EE $2,500 / PP $5,000',  # OQ42's default: both figures
        'oop_max_single': 'EE $5,000 / PP $6,850',
        'deductible_family': '5000',
        'oop_max_family': '10000',
        'deductible_single_oon': 'EE $5,000 / PP $10,000',
        'deductible_family_oon': '10000',
        'oop_max_single_oon': 'EE $10,000 / PP $20,000',
        'oop_max_family_oon': '20000',
        'rate_ee': '1105.26',
        'rate_es': '2520.00',
        'rate_ec': '2210.52',
        'rate_fam': '3625.26',
        'coinsurance': '10',
    }
    assert (column.name, column.plan_number) == ('BlueOptions HSA Compatible 05182 + 05183', '05182 / 05183')
    assert (column.id, column.pair, column.own_name) == (1, (1, 2), ee.name)


def test_J15_the_employee_only_half_is_found_by_its_rates_not_the_order():
    ee = _row(1, 'HSA 05182', '05182', HALF_EE)
    dep = _row(2, 'HSA 05183', '05183', HALF_DEP, recommended=True)
    column = pair_fold.column(dep, ee)
    assert column.id == 2, 'the column keeps the first plan of the pair'
    assert column.pair == (1, 2) and column.values['oop_max_single'] == 'EE $5,000 / PP $6,850'
    assert column.name == 'HSA 05182 + 05183' and column.recommended


def test_J15_names_share_their_words_and_other_values_print_both():
    assert pair_fold.merged_name('Gold PPO', 'Silver HMO') == 'Gold PPO + Silver HMO'
    assert pair_fold.merged_name('HSA 05182', 'HSA 05182') == 'HSA 05182'
    ee = _row(1, 'A', '', {'pcp_copay': '10', 'group_premium_monthly': '100.25'})
    dep = _row(2, 'B', '', {'pcp_copay': '20', 'group_premium_monthly': '200.50'})
    values = pair_fold.column(ee, dep).values
    assert values['pcp_copay'] == 'EE only $10 / with dependents $20'
    assert values['group_premium_monthly'] == '300.75', 'a quoted premium is the two added (quotes.math)'


def _laid(deal):
    state = selectors.line_state(deal, 'medical')
    stored = line_layout.stored_config(deal)
    return line_layout.lay_out(state, None, line_layout.layout_of(stored), 0), state


def test_J15_J159_GD1_the_pair_is_one_column_priced_as_its_package_under_the_first_number(gd1, golden_keys):
    deal, refs, _spec = gd1
    laid, state = _laid(deal)
    first, second = refs['FB1'], refs['FB2']
    assert laid.pairs == {first: second}
    printed = [pid for page in laid.pages for pid in page['plan_ids']]
    assert first in printed and second not in printed
    package = pk.package([first, second], state.data, state.results)
    got = laid.state.results[first]
    key = golden_keys['GD1']['pairs']['FB1+FB2']
    assert (got['monthly'], got['annual'], got['change']) == (key['monthly'], key['annual'], key['change'])
    assert got['monthly'] == package['monthly']
    assert laid.options[first] and second not in laid.options, 'the column keeps the first plan’s number'
    assert second not in line_layout.reading_ids(deal), 'Issue stamps no number on the second half'


def test_J15_F137_GD1_pages_print_one_column_and_split_restores_two(api, gd1):
    deal, refs, _spec = gd1
    first, second = refs['FB1'], refs['FB2']
    url = f'/api/deals/{deal.id}/proposal/pages/?line=medical&preset=primary'
    pages = api.get(url).json()
    columns = {plan['plan_id']: plan for plan in pages['plans']}
    assert second not in columns
    column = columns[first]
    assert column['name'] == 'BlueOptions HSA Compatible 05182'
    assert column['pair']['state'] == 'paired' and column['pair']['folded']
    assert column['pair']['with'] == 'BlueOptions HSA Compatible 05183'
    assert (column['monthly'], column['remove']['also']) == ('$15,257', [second])
    cells = {row['key']: row['cells'] for row in pages['rows']}
    assert cells['deductible_single'][str(first)] == 'EE $2,500 / PP $5,000'
    before = len([pid for page in pages['pages'] for pid in page['plan_ids']])

    split = api.post(f'/api/deals/{deal.id}/plans/pair/', {'plan_ids': [second], 'split': True}, format='json')
    assert split.status_code == 200
    pages = api.get(url).json()
    columns = {plan['plan_id']: plan for plan in pages['plans']}
    assert {first, second} <= set(columns) and columns[first]['monthly'] == '$4,604'
    assert columns[first]['pair']['state'] == 'open'
    assert len([pid for page in pages['pages'] for pid in page['plan_ids']]) == before + 1
    checks = [item['code'] for item in api.get(f'/api/deals/{deal.id}/proposal/').json()['checks']]
    assert 'split_plan' in checks, 'one plan filed as two is pointed out until it is paired'

    again = api.post(f'/api/deals/{deal.id}/plans/pair/', {'plan_ids': [first, second]}, format='json')
    assert again.status_code == 200
    checks = [item['code'] for item in api.get(f'/api/deals/{deal.id}/proposal/').json()['checks']]
    assert 'split_plan' not in checks


def _pdf_text(api, deal):
    response = api.get(f'/api/deals/{deal.id}/proposal/files/pdf/')
    reader = PdfReader(io.BytesIO(b''.join(response.streaming_content)))
    return ' '.join(' '.join((page.extract_text() or '').split()) for page in reader.pages)


def _pptx_text(api, deal):
    response = api.get(f'/api/deals/{deal.id}/proposal/files/pptx/')
    deck = Presentation(io.BytesIO(b''.join(response.streaming_content)))
    found = []
    for slide in deck.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                found.append(shape.text_frame.text)
            if shape.has_table:
                found.extend(cell.text for row in shape.table.rows for cell in row.cells)
    return ' '.join(' '.join(found).split())


def _book_texts(deal):
    book = workbook.book(deal)
    return {
        sheet.title: [str(cell.value) for cell in sheet.cells.values() if cell.value is not None]
        for sheet in book.sheets
    }


def test_J15_GD1_the_three_files_print_one_column(api, gd1):
    deal, _refs, _spec = gd1
    pdf, deck = _pdf_text(api, deal), _pptx_text(api, deal)
    for text in (pdf, deck):
        assert 'BlueOptions HSA Compatible 05182 + 05183' in text
        assert 'EE $2,500 / PP $5,000' in text
        assert '05183 ' not in text.replace('05182 + 05183', ''), 'no page prints 05183 alone'
        assert '$15,257' in text
    texts = _book_texts(deal)
    assert any('05182 + 05183' in value for value in texts['Medical'])
    for title, values in texts.items():
        alone = [v for v in values if 'BlueOptions' in v and '05183' in v and '+' not in v]
        assert not alone, f'{title} lists 05183 alone'


def test_J15_GD1_split_prints_two_columns_again(api, user, gd1):
    deal, refs, _spec = gd1
    plans.split_pair(user, deal, refs['FB2'])
    pdf = _pdf_text(api, deal)
    assert 'BlueOptions HSA Compatible 05183' in pdf and '05182 + 05183' not in pdf
