"""The answer's other pages and how we got here (plan.md §9.5; J127, J128, J130; old Vantage 891f1b3
`proposal_presentation._negotiation_page`, `_chart_page`, `_summary_page`, `_experience_page`, `_markets_page`).
Pure.

- What we negotiated: the carrier's first %, ours, and the dollars between, on tiles, with the journey charted when
  one line moved; a table when several did.
- The premiums charted: today beside what we recommend, line by line, only with two or more rows (a native chart in
  the PowerPoint).
- The executive summary as a dashboard: the deal's figures on tiles (not those the overview already printed), the
  lines' side by side, one column per kind of figure. Only the blocks that could be worked out (J64).
- Plan experience: the producer's typed totals and summary, the loss ratio derived (J130). No row a person could
  occupy.
- Markets checked: per line, each carrier asked, whether it quoted, whether it is on this proposal, and the note; a
  carrier the producer hid never prints (J63).
"""

from ..layout import cards, tokens
from ..layout import table as tb
from ..layout import text as words
from . import glance as figures
from . import look

ON_THE_OVERVIEW = frozenset({'total_current', 'total_recommended', 'total_annual_delta'})
QUOTED_WORD = {True: 'Yes', False: 'No', None: '–'}
BODY_W = tokens.BODY_W


def negotiation(facts, glance, plans_by_id):
    entries = figures.negotiated(glance, plans_by_id)
    if not entries:
        return []
    colours = look.colours_of(facts)
    lead = entries[0]
    title = f'{lead["label"]}: what we negotiated' if len(entries) == 1 else 'What we negotiated'
    gap = 18
    width = (BODY_W - 2 * gap) / 3
    first_sub = f'{look.money(lead["first_annual"])} a year' if lead['first_annual'] else ''
    placed = cards.tile(
        0,
        8,
        width,
        150,
        look.pct(lead['first_pct']),
        "The carrier's first offer",
        colours,
        sub=first_sub,
        size=46,
        ground=colours['current'],
    )
    placed += cards.tile(
        width + gap,
        8,
        width,
        150,
        look.pct(lead['final_pct']),
        'After our negotiation',
        colours,
        sub=f'{look.money(lead["final_annual"])} a year',
        size=46,
    )
    if lead['saved']:
        placed += cards.tile(
            2 * (width + gap),
            8,
            width,
            150,
            look.money(lead['saved']),
            'Saved in the first year',
            colours,
            dark=True,
            size=46,
        )
    story = [look.title(title), look.block(placed, 172)]
    if len(entries) == 1:
        chart = cards.bars(
            0,
            0,
            BODY_W,
            238,
            ['What you pay today', "The carrier's first offer", 'After our negotiation'],
            [
                {
                    'name': lead['label'],
                    'color': colours['blue'],
                    'values': [lead['today_annual'], lead['first_annual'], lead['final_annual']],
                    'colors': [colours['silver'], colours['ink2'], colours['blue']],
                }
            ],
        )
        story.append(look.block([chart], 242))
    else:
        rows = [look.heads(['Coverage', 'First offer', 'After our negotiation', 'Saved in the first year'], colours)]
        for entry in entries:
            texts = [entry['label'], look.pct(entry['first_pct']), look.pct(entry['final_pct'])]
            rows.append(look.row([*texts, look.money(entry['saved'])], colours))
        story.append(look.grid(rows, look.shares([0.4, 0.2, 0.2, 0.2]), colours))
    saved = f' That is {look.money(lead["saved"])} in the first year.' if lead['saved'] else ''
    story.append(
        look.note(
            f'The carrier opened at {look.pct(lead["first_pct"])}. We brought it to {look.pct(lead["final_pct"])}.'
            + saved
        )
    )
    return [story]


def chart(facts, glance):
    rows = [row for row in glance or [] if row['today'] is not None and row['recommended'] is not None]
    if len(rows) < 2:
        return []
    colours = look.colours_of(facts)
    labels = [row['label'] if not row['replacing'] else f'{row["label"]} ({row["replacing"]})' for row in rows]
    series = [
        {'name': 'Today', 'values': [row['today'] for row in rows], 'color': colours['silver']},
        {'name': 'Recommended', 'values': [row['recommended'] for row in rows], 'color': colours['blue']},
    ]
    return [
        [
            look.title('What you pay today and what we recommend'),
            look.block([cards.bars(0, 0, BODY_W, 400, labels, series)], 410),
        ]
    ]


def _line_cell(block, size, colours):
    runs = [words.run(block.get('value_label') or '—', size, colours['ink'], True)]
    if block.get('delta_label'):
        runs.append(words.run(f' {block["delta_label"]}', size - 1, colours['ink']))
    if block.get('sub'):
        runs.append(words.run(f'\n{block["sub"]}', size - 1.5, colours['ink2']))
    return tb.rich(runs)


def summary(facts, overview_printed):
    found = facts['summary']
    if not found['on']:
        return []
    blocks = found['blocks']
    deal = [b for b in blocks if b['scope'] != 'line' and not (overview_printed and b['key'] in ON_THE_OVERVIEW)]
    lines = [b for b in blocks if b['scope'] == 'line']
    if not deal and not lines:
        return []
    colours = look.colours_of(facts)
    story = [look.title('Executive summary')]
    if deal:
        entries = [(b['label'], b.get('value_label') or '—', (b.get('sub') or '')[:70], False) for b in deal[:4]]
        story.append(look.block(cards.tiles(entries, colours, BODY_W, 92, 22), 100))
        for block in deal[4:]:
            story.append(look.lead_para(f'{block["label"]}:', block.get('value_label') or '', 'sub', colours))
    if lines:
        labels, by_line = [], {}
        for block in lines:
            if block['label'] not in labels:
                labels.append(block['label'])
            by_line.setdefault(block.get('line_label') or block['line'], {})[block['label']] = block
        labels = labels[:5]
        label_w = BODY_W * 0.18
        width = (BODY_W - label_w) / max(1, len(labels))
        size = 11 if len(by_line) <= 6 else 9.5
        rows = [look.heads(['Coverage', *labels], colours, size)]
        for name, row in by_line.items():
            cells = [tb.cell(name, size, colours['ink'], True)]
            for label in labels:
                block = row.get(label)
                cells.append(_line_cell(block, size, colours) if block else tb.cell('—', size, colours['ink']))
            rows.append({'kind': 'plain', 'cells': cells})
        story.append(look.grid(rows, [label_w] + [width] * len(labels), colours))
    return [story]


def experience(facts):
    found = facts['experience']
    if not found['rows'] and not found['summary']:
        return []
    colours = look.colours_of(facts)
    story = [look.title('Your plan experience')]
    if found['summary']:
        story += [look.para(found['summary'], 'intro', colours, space_after=10)]
    if found['rows']:
        rows = [look.heads(['Period', 'Premium', 'Paid claims', 'Loss ratio'], colours)]
        for row in found['rows']:
            cells = [tb.cell(row['period'], 12, colours['ink'], True)]
            cells += [
                tb.cell(row[key], 12, colours['ink'], key == 'ratio', 'c') for key in ('premium', 'claims', 'ratio')
            ]
            rows.append({'kind': 'plain', 'cells': cells})
        story.append(look.grid(rows, look.shares([0.4, 0.2, 0.2, 0.2]), colours, pad=6))
    return [story]


def markets(facts):
    found = facts['markets']
    lines = [line for line in found['lines'] if any(not row['hidden'] for row in line['rows'])]
    if not found['on'] or not lines:
        return []
    colours = look.colours_of(facts)
    size = 10.5
    widths = look.shares([0.3, 0.1, 0.13, 0.47])
    story = [look.title('Markets checked')]
    for line in lines:
        rows = [look.heads([line['label'], 'Quoted', 'On this proposal', 'Notes'], colours, size)]
        rows[0]['cells'][3]['align'] = 'l'
        for row in line['rows']:
            if row['hidden']:
                continue
            ink = colours['ink']
            carrier = row['carrier'] + (' (current)' if row['current'] else '')
            cells = [tb.cell(carrier, size, ink), tb.cell(QUOTED_WORD.get(row['quoted'], '–'), size, ink, align='c')]
            cells += [
                tb.cell('Yes' if row['presented'] else 'No', size, ink, align='c'),
                tb.cell(row['note'], size, ink),
            ]
            rows.append({'kind': 'plain', 'cells': cells})
        story += [look.grid(rows, widths, colours, pad=2.6), look.gap(8)]
    return [story]
