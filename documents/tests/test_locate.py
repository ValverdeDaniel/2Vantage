"""The locator (plan.md §10.7; E81–E83, D-122, D-164, D-209): a table of states over synthetic text, and the files it
opens. Pure: no database."""

import io

import pytest

import synthetic_files
from documents.locate import (
    ABSENT,
    FOUND,
    NOCHECK,
    Located,
    PdfIndex,
    Query,
    SheetIndex,
    guard_text_layer,
    locate_all,
    open_index,
    reader_line,
)
from documents.locate.sheet_cells import visible_sheets

from .helpers import RATES_PDF, xlsx

PAGES = [
    'Acme Health Quote\nPlan: Gold 1500 PPO\nEffective 1/1/2026',
    'Benefit Gold 1500 Silver 3000\n'
    'Deductible $1,500 / $3,000 $3,000 / $6,000\n'
    'Office visit copay $25 $40\n'
    'Coinsurance 20% 30%\n'
    'Monthly premium $ 512.37 $498.10',
    '',
    'Plan code PD 5500-2027\nAnnual {lig}ling fee {dash} $1,200',
]
ALLOWED_KEYS = {'state', 'page', 'sheet', 'cell', 'hits', 'via', 'why', 'printed'}


@pytest.fixture(scope='module')
def index():
    return PdfIndex([page.format(lig=chr(0xFB01), dash=chr(0x2013)) for page in PAGES])


def where(index, query):
    return index.locate(query).as_dict()


@pytest.mark.parametrize(
    'query, expected',
    [
        (Query('512.37', page=2), {'state': 'found', 'page': 2, 'via': 'number', 'hits': 1}),
        (Query('$1,500.00', page=2), {'state': 'found', 'page': 2}),  # "$1,500" inside a money pair
        (Query('498.1', page=2), {'state': 'found', 'page': 2}),  # against "$498.10"
        (Query('9999', page=2), {'state': 'absent'}),
        (Query('3000', page=1), {'state': 'found', 'page': 2}),  # found on another page names that page
        (Query('25', page=2), {'state': 'weak', 'page': 2}),  # a common figure with no word on its line
        (Query('25', page=2, anchors=('Office visit',)), {'state': 'found', 'page': 2}),
        (Query('PD55002027', kind='code'), {'state': 'found', 'page': 4, 'via': 'code'}),
        (Query('01/01/2026'), {'state': 'found', 'page': 1}),  # a date in another printed form
        (Query('filing fee - $1,200'), {'state': 'found', 'page': 4}),  # a ligature and an en dash fold
        (Query('Preferred Provider', strict=False), {'state': 'weak', 'why': 'reworded'}),
        (Query('100', page=3), {'state': 'nocheck', 'page': 3, 'why': 'no_text'}),  # a scanned page
        (Query('ab'), {'state': 'nocheck', 'why': 'short'}),
    ],
)
def test_E81_locator_states_on_a_pdf(index, query, expected):
    found = where(index, query)
    assert {key: found.get(key) for key in expected} == expected


def test_E81_a_reader_rule_is_derived_and_names_what_is_printed(index):
    # The member's coinsurance is recorded as 100 minus the plan's share: 80 is printed nowhere, 20 is.
    found = where(index, Query('80', page=2, anchors=('coinsurance',), alternatives=(('20', 'complement'),)))
    assert (found['state'], found['via'], found['printed']) == ('derived', 'complement', '20')


def test_E81_no_charge_words_record_zero_beside_their_row():
    pages = PdfIndex(['Gold 1500 benefits\nPreventive care No charge\nSpecialist $50 copay'])
    found = pages.locate(Query('0', anchors=('preventive',), wordings=(('no charge', 'no_charge'),)))
    assert (found.state, found.via, found.printed) == ('derived', 'no_charge', 'no charge')


def test_E81_design_dollars_match_within_their_tolerance():
    pages = PdfIndex(['Silver plan deductible $1,499.50 per person'])
    assert pages.locate(Query('1500', tolerance=1.0)).state == FOUND
    assert pages.locate(Query('1500')).state == ABSENT


def test_E81_a_file_of_scanned_pages_cannot_say():
    assert PdfIndex(['', ' ']).locate(Query('512.37')).as_dict() == {'state': 'nocheck', 'why': 'no_text'}


def test_E81_an_absence_beside_image_pages_says_so():
    pages = PdfIndex(['Gold 1500 rates employee 512.37 family 1580.47', ''])
    assert pages.locate(Query('777.77')).as_dict() == {'state': 'absent', 'why': 'image_pages'}
    assert pages.locate(Query('777.77', page=1)).as_dict() == {'state': 'absent'}


SNIPPET_PAGES = [
    'Plan summary\nGold 1500 Coinsurance 80% Rx deductible $0',
    'Gold 1500 rates\nEmployee 512.37',
    'Gold 1500 in-network benefits\nCoinsurance\n80% after deductible\n'
    'Primary care 100% after $20 copayment\nPrescription Drug Deductible Individual None',
]


def snippet_where(value, page, snippet='', label='Coinsurance'):
    query = Query(value, page=page, anchors=('Gold 1500', label), snippet=snippet)
    return PdfIndex(SNIPPET_PAGES).locate(query).as_dict()


def test_E81_the_readers_line_on_its_page_outranks_a_figure_elsewhere():
    assert snippet_where('80', 3)['page'] == 1  # without the line, the anchored "80%" on page 1 wins
    found = snippet_where('80', 3, snippet='80% after deductible')
    assert (found['state'], found['page'], found['via']) == ('found', 3, 'number')
    found = snippet_where('20', 3, snippet='100% after $20 copayment', label='Primary care')
    assert (found['state'], found['page']) == ('found', 3)


def test_E81_a_reworded_line_keeps_the_value_on_its_page_but_weak():
    found = snippet_where('0', 3, snippet='Prescription Drug Deductible Individual None', label='Rx deductible')
    assert found == {'state': 'weak', 'page': 3, 'why': 'reworded'}


def test_E81_a_line_not_on_its_page_changes_nothing():
    assert snippet_where('80', 2, snippet='80% after deductible')['page'] == 1
    assert snippet_where('80', 3, snippet='80%')['page'] == 1  # too short to say anything


def test_E81_the_printed_note_is_not_part_of_the_readers_line():
    assert reader_line('80% after deductible · printed "80%"') == '80% after deductible'
    assert reader_line('printed "80%"') == ''


def test_E81_a_nonsense_text_layer_is_not_a_wall_of_misreads():
    results = [Located(ABSENT) for _ in range(7)] + [Located(FOUND, page=1) for _ in range(3)]
    guard_text_layer(results)
    assert {result.state for result in results} == {NOCHECK, FOUND}
    assert results[0].why == 'text_layer'
    assert guard_text_layer([Located(ABSENT) for _ in range(3)])[0].state == ABSENT


def test_E81_an_answer_never_carries_the_files_text(index):
    for query in (Query('512.37', page=2), Query('Office visit copay $25'), Query('PD55002027', kind='code')):
        found = where(index, query)
        assert set(found) <= ALLOWED_KEYS
        assert all(isinstance(value, int) or len(str(value)) <= 12 for value in found.values()), found
    found = snippet_where('80', 3, snippet='80% after deductible')
    assert 'deductible' not in str(found)


def test_E81_sheets_name_the_cell():
    sheets = SheetIndex(
        [
            (
                'Rates',
                [
                    ['Benefit', 'Gold 1500', 'Silver 3000'],
                    ['Premium', '512.37', '498.1'],
                    ['Effective', '01/01/2026', ''],
                    ['Deductible', '$1,500 / $3,000', '3000'],
                    ['Copay', '25', '40'],
                ],
            )
        ]
    )
    assert sheets.locate(Query('512.37')).as_dict() == {
        'state': 'found',
        'sheet': 'Rates',
        'cell': 'B2',
        'via': 'number',
        'hits': 1,
    }
    assert sheets.locate(Query('3000')).cell == 'C4'  # an exact cell beats a pair holding the figure
    assert sheets.locate(Query('1500', hint='Gold 1500')).cell == 'B4'  # a pair beats a name
    assert sheets.locate(Query('2026-01-01')).cell == 'B3'
    assert sheets.locate(Query('40', anchors=('copay',), hint='Silver 3000')).cell == 'C5'
    assert sheets.locate(Query('25')).state == 'weak'
    assert sheets.locate(Query('nowhere')).as_dict() == {'state': 'absent'}


def test_E82_the_locator_reads_visible_cells_only():
    rows = [['Plan', 'Gold PPO 1500', 'Hidden code'], ['Employee only', 512.34, 'UW-77'], ['Factor', 0.97, '']]
    content = xlsx(rows, hidden_rows=[2], hidden_cols=[2], extra_sheets=[('Notes', True)])
    sheets = visible_sheets('quote.xlsx', content)
    assert [name for name, _rows in sheets] == ['Rates']  # the hidden sheet is left out
    index, why = open_index('quote.xlsx', content)
    assert why == ''
    assert index.locate(Query('512.34')).as_dict()['cell'] == 'B2'
    assert index.locate(Query('UW-77')).state == ABSENT  # a hidden column
    assert index.locate(Query('0.97')).state == ABSENT  # a hidden row
    assert index.locate(Query('Gold PPO 1500')).cell == 'B1'


def test_E82_a_csv_sheet_is_named_as_the_viewer_names_it():
    index, _why = open_index('rates.csv', b'Plan,EE\nGold,450.25\n')
    assert index.locate(Query('450.25')).as_dict()['sheet'] == 'Sheet1'


@pytest.mark.parametrize(
    'name, content, why',
    [
        ('scan.png', synthetic_files.png(), 'image'),
        ('letter.docx', b'PK\x03\x04 not really', 'format'),
        ('broken.pdf', b'%PDF-1.4 nothing else', 'unreadable'),
        ('broken.xlsx', b'PK\x03\x04 not a workbook', 'unreadable'),
    ],
)
def test_E81_a_file_it_cannot_search_says_why(name, content, why):
    index, reason = open_index(name, content)
    assert (index, reason) == (None, why)
    assert [result.as_dict() for result in locate_all(index, reason, [Query('512.34')])] == [
        {'state': 'nocheck', 'why': why}
    ]


def test_E81_too_many_pages_is_not_searched():
    assert open_index('big.pdf', RATES_PDF, page_count=1501) == (None, 'too_large')


def test_E81_a_pdf_reads_page_by_page_and_can_stop_between_pages():
    seen = []
    index, _why = open_index('rates.pdf', RATES_PDF, on_page=lambda number, total: seen.append((number, total)))
    assert seen == [(1, 2), (2, 2)]
    assert index.locate(Query('512.34')).as_dict()['page'] == 2

    class Stop(Exception):
        pass

    def stop(number, total):
        raise Stop

    with pytest.raises(Stop):
        open_index('rates.pdf', RATES_PDF, on_page=stop)


def test_E81_locate_all_passes_an_owners_answer_through_and_guards_a_pdf(index):
    owners = Located(NOCHECK, why='choice')
    queries = [owners, *[Query(f'{9000 + n}.11', page=2) for n in range(8)], Query('512.37', page=2)]
    states = [result.state for result in locate_all(index, '', queries)]
    assert states[0] == NOCHECK and states[-1] == FOUND
    assert set(states[1:-1]) == {NOCHECK}  # eight absences out of nine: the text layer is suspect


def _fillable_pdf():
    """A one-page PDF whose answer sits in a filled text field beside its printed label (D-209)."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import ArrayObject, DictionaryObject, FloatObject, NameObject, TextStringObject

    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(synthetic_files.pdf([[(72, 700, 'Employer TIN:'), (72, 660, 'Plan year')]]))))
    field = DictionaryObject(
        {
            NameObject('/Type'): NameObject('/Annot'),
            NameObject('/Subtype'): NameObject('/Widget'),
            NameObject('/FT'): NameObject('/Tx'),
            NameObject('/T'): TextStringObject('tin'),
            NameObject('/V'): TextStringObject('52-1234567'),
            NameObject('/Rect'): ArrayObject([FloatObject(v) for v in (160, 695, 300, 712)]),
        }
    )
    reference = writer._add_object(field)
    writer.pages[0][NameObject('/Annots')] = ArrayObject([reference])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def test_E81_a_forms_answers_are_found_on_their_labels_line():
    index, _why = open_index('form.pdf', _fillable_pdf())
    found = index.locate(Query('52-1234567', snippet='Employer TIN: 52-1234567', page=1))
    assert (found.state, found.page) == ('found', 1)


def test_E81_one_figure_under_two_plans_opens_each_plans_own_cell():
    sheets = SheetIndex(
        [
            (
                'Medical',
                [
                    ['Benefit', 'LocalPlus HDHP 3000', 'LocalPlus HDHP 3500'],
                    ['OOP Max (Single)', '6500', '6500'],
                    ['Plan Type', 'HDHP', 'HDHP'],
                ],
            )
        ]
    )
    for hint, cell in (('Cigna LocalPlus HDHP 3000', 'B2'), ('Cigna LocalPlus HDHP 3500', 'C2')):
        assert sheets.locate(Query('6500', anchors=('OOP Max (Single)',), hint=hint)).cell == cell
        plan_type = Query('HDHP', anchors=('Plan Type',), hint=hint, strict=False)
        assert sheets.locate(plan_type).cell == cell.replace('2', '3')
    # A transposed sheet (plans in rows) crosses the other way.
    turned = SheetIndex([('Rates', [['Plan', 'OOP Max (Single)'], ['Gold 1500', '6500'], ['Gold 2000', '6500']])])
    assert turned.locate(Query('6500', anchors=('OOP Max (Single)',), hint='Acme Gold 2000')).cell == 'B3'
