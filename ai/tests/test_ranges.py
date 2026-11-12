"""How a file is cut into the parts one call reads (plan.md §10.4, §10.8; D49, D50, D52, OQ22; slice 18). Pure."""

from ai import ranges

HEADER, FOOTER = 'Example Health · Group renewal', 'Confidential · rates are monthly'


def page(*lines, number=1, total=4):
    return '\n'.join([HEADER, *lines, FOOTER, f'Page {number} of {total}'])


def test_D49_pages_with_only_the_running_header_and_footer_are_left_out():
    texts = [
        page('Dear partner, enclosed are your rates.', number=1),
        page('Gold PPO 1500 $512.34', number=2),
        page(number=3),
        page('Silver HMO 3000 $410.50', number=4),
    ]
    parts, out = ranges.pdf_ranges(texts)
    assert out == {3: ranges.HEADER_ONLY}
    assert [part.pages for part in parts] == [(1, 2), (4,)]  # never across a left-out page


def test_D52_OQ22_screened_pages_are_left_out_only_as_given_and_scanned_pages_never():
    texts = [page('Rates $1.00', number=1), '', page('Roster', number=3), page('More $2.00', number=4)]
    parts, out = ranges.pdf_ranges(texts, screened=[3])
    assert out == {3: ranges.SCREENED}
    assert parts[0].pages == (1, 2)  # page 2 has no text layer: kept, estimated at a fixed size
    parts, out = ranges.pdf_ranges(texts)
    assert out == {} and [part.pages for part in parts] == [(1, 2, 3, 4)]


def test_D49_a_range_stays_under_a_quarter_of_max_tokens():
    dense = ' '.join(f'${n}.25' for n in range(400))  # 400 figures, about 7,500 output tokens a page
    parts, _ = ranges.pdf_ranges([dense] * 10, max_tokens=128_000)
    assert len(parts) > 1 and all(part.est_output <= 32_000 for part in parts)
    assert [page for part in parts for page in part.pages] == list(range(1, 11))


def test_D50_a_cut_off_range_halves_and_one_page_cannot():
    whole = ranges.Range(ranges.PDF, pages=(1, 2, 3), est_input=6000, est_output=900)
    first, second = ranges.halve(whole)
    assert (first.pages, second.pages) == ((1,), (2, 3))
    assert ranges.halve(first) is None
    sheet = ranges.Range(ranges.SHEET, sheet='Rates', rows=(1, 9), est_input=100, est_output=100)
    assert [part.rows for part in ranges.halve(sheet)] == [(1, 5), (6, 9)]


def test_E82_hidden_sheets_are_never_read_and_long_sheets_go_in_windows():
    rows = [['Plan', 'Gold'], ['Employee only', '512.34']] * 300
    parts = ranges.sheet_ranges(
        [{'name': 'Rates', 'rows': rows, 'hidden': False}, {'name': 'Notes', 'rows': [['x']], 'hidden': True}]
    )
    assert {part.sheet for part in parts} == {'Rates'}
    assert [part.rows for part in parts] == [(1, 400), (401, 600)]
    assert parts[0].label == 'sheet:Rates:1-400' and parts[0].where() == 'a sheet, rows 1–400'


def test_D65_labels_name_the_pages_for_the_fake_and_the_job():
    assert ranges.Range(ranges.PDF, pages=(2, 3)).label == 'p2-3'
    assert ranges.Range(ranges.PDF, pages=(2,)).label == 'p2'
    assert ranges.Range(ranges.PDF, pages=(2, 5)).label == 'p2,5'
    assert ranges.Range(ranges.PDF, pages=(2, 3)).where() == 'pages 2–3'
