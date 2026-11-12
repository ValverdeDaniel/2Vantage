"""The overview and the coverage that has nothing to compare (plan.md §9.5; J126, J137; old Vantage 891f1b3
`proposal_presentation._overview_page`, `next_renewal_label`, `_kept_lines` and `proposal_pdf._nothing_to_compare_
flowables`). Pure.

The overview answers first: tiles with what the client pays today, what we recommend, what negotiating saved and the
change; then one row per line (or per current plan on a line with several), the lines kept as they are (on the
proposal, not marketed: often rate-guaranteed), and the total when it is honest. Its table takes the largest type
that fits the page. A line kept as it is prints here only: 2V's coverage rows hold no plan design or rates of their
own, so the old incumbent page (printed only when it said more than this row) has nothing more to say.
"""

import datetime

from quotes import math as m

from ..layout import cards, fit, flowables, tokens
from ..layout import table as tb
from ..layout import text as words
from . import glance as figures
from . import look


def next_renewal(guarantee, effective):
    """When a line next renews: the day after its rate guarantee ends, else a year after the effective date."""
    found = look.iso_date(guarantee) if guarantee else None
    if found is not None:
        day = found + datetime.timedelta(days=1)
    elif effective:
        try:
            day = effective.replace(year=effective.year + 1)
        except ValueError:  # February 29
            day = effective.replace(year=effective.year + 1, day=28)
    else:
        return ''
    return f'{day.month}/{day.day}/{day.year}'


def _first_pct(row, plans_by_id):
    """The carrier's first % on a row: a negotiated plan's original against today."""
    first = (plans_by_id.get(row['plan_id']) or {}).get('first')
    if not first or first.get('annual') is None or not row['today'] or row['kept']:
        return ''
    change = m.change(first['annual'], row['today'])
    return look.pct(change['pct']) if change and change['pct'] is not None else ''


def _tiles(total, saved, colours):
    if not total:
        return None
    entries = [
        ('What you pay today', look.money(total['today']), 'a year', False),
        ('What we recommend', look.money(total['recommended']), 'a year', False),
        ('The change', look.signed(total['delta']), look.pct(total['pct']), True),
    ]
    if saved:
        entries.insert(2, ('Saved by negotiating', look.money(m.add(saved)), 'a year', False))
    return look.block(cards.tiles(entries, colours, tokens.BODY_W, 76, 24, most=10**6), 84)


def overview(facts, plans_by_id):
    """The overview page, or [] until anything is recommended (and no line is kept)."""
    rows = figures.rows(facts['glance_facts']) or []
    kept = facts['kept']
    if not rows and not kept:
        return []
    colours = look.colours_of(facts)
    guarantee = {line['key']: line['guarantee'] for line in facts['lines']}
    effective = facts['effective']
    total = figures.total(facts['glance_facts']) if rows else None
    saved = [entry['saved'] for entry in figures.negotiated(rows, plans_by_id) if entry['saved']]
    heading = f'{facts["year"]} renewal overview' if facts['renewal'] and facts['year'] else None
    story = [look.title(heading or 'Our recommendation at a glance')]
    if facts['intro']:
        story += [look.para(facts['intro'], 'intro', colours, space_after=6)]
    tiles = _tiles(total, saved, colours)
    if tiles:
        story.append(tiles)
    firsts = {id(row): _first_pct(row, plans_by_id) for row in rows}
    nexts = {id(row): next_renewal(guarantee.get(row['line']), effective) for row in rows}
    kept_next = {line['key']: next_renewal(line['incumbent'].get('rate_guarantee_through'), effective) for line in kept}
    with_first, with_next = any(firsts.values()), any(nexts.values()) or any(kept_next.values())
    heads, shares = ['Coverage', 'Recommended'], [0.25, 0.27]
    if with_next:
        heads, shares = [*heads, 'Next renewal'], [*shares, 0.09]
    if with_first:
        heads, shares = [*heads, 'First offer'], [*shares, 0.08]
    heads, shares = [*heads, 'Today', 'Proposed', 'Change', '%'], [*shares, 0.11, 0.11, 0.1, 0.07]
    widths = look.shares(shares)
    below = []
    if total and total['credit']:
        below.append(look.para(f'After {look.money(total["credit"])} in first-year credits.', 'note', colours))
    if kept:
        below.append(
            look.para(
                'Coverage marked Keep is presented as currently in force; it was not sent to market this cycle.',
                'note',
                colours,
            )
        )

    def build(size, pad):
        small, ink, soft = size - 1.5, colours['ink'], colours['ink2']
        data = [look.heads(heads, colours, size, center_from=2)]
        for row in rows:
            runs = [words.run(row['label'], size, ink, True)]
            if row['replacing']:
                runs.append(words.run(f'\nIn place of {row["replacing"]}', small, soft))
            if guarantee.get(row['line']) and row['delta'] in (None, 0):
                runs.append(
                    words.run(
                        f'\nRate guaranteed through {look.long_date(look.iso_date(guarantee[row["line"]]))}',
                        small,
                        soft,
                    )
                )
            cells = [tb.rich(runs), tb.cell(row['name'] or '—', size, ink)]
            texts = ([nexts[id(row)] or '—'] if with_next else []) + ([firsts[id(row)] or '—'] if with_first else [])
            texts += [look.money(row['today']), look.money(row['recommended']), look.signed(row['delta'])]
            texts += [look.pct(row['pct'])]
            cells += [tb.cell(text, size, ink, align='c') for text in texts]
            data.append({'kind': 'plain', 'cells': cells})
        for line in kept:
            card = line['incumbent']
            through = card.get('rate_guarantee_through')
            keep = f'Keep {card.get("carrier") or "your current plan"}'
            if through:
                keep += f' · rate guaranteed through {look.long_date(look.iso_date(through))}'
            cells = [tb.cell(line['label'], size, ink, True), tb.cell(keep, size, ink)]
            texts = ([kept_next[line['key']] or '—'] if with_next else []) + (['—'] if with_first else []) + ['—'] * 4
            data.append({'kind': 'plain', 'cells': cells + [tb.cell(t, size, ink, align='c') for t in texts]})
        if total:
            lead = len(heads) - 4
            figures_ = (look.money(total['today']), look.money(total['recommended']), look.signed(total['delta']))
            cells = [tb.cell('Total', size, ink, True), *[tb.cell('', size, ink) for _ in range(lead - 1)]]
            cells += [tb.cell(text, size, ink, True, 'c') for text in (*figures_, look.pct(total['pct']))]
            data.append({'kind': 'total', 'cells': cells, 'fill': colours['blue_bg'], 'rule_above': colours['navy']})
        return look.grid(data, widths, colours, pad=pad)

    above = fit.height_under([f for f in story[1:] if not isinstance(f, flowables.Title)])
    room = tokens.BODY_H - above - fit.height_under(below) - 2
    found = fit.fitted(build, room, largest=11)
    story.append(found[0] if found else build(tokens.TABLE_TYPE['floor'], tokens.TIGHTEST_PAD))
    story += below
    if total:
        story.append(
            look.note(
                f'Start here. Today the program costs {look.money(total["today"])} a year. What we recommend costs '
                f'{look.money(total["recommended"])}, a change of {look.signed(total["delta"])} '
                f'({look.pct(total["pct"])}).'
            )
        )
    if facts['recommendation']:
        story.append(look.note(facts['recommendation']))
    return [story]


def advisor(facts):
    name = (facts['agency']['name'] or '').strip()
    return f'your {name} benefits advisor' if name else 'your benefits advisor'


def nothing_to_compare(facts):
    """The page a deal with nothing to compare still gets, so a proposal is never blank: one plain sentence."""
    colours = look.colours_of(facts)
    page = [look.title('Your coverage')]
    if facts['recommendation']:
        page.append(look.para(facts['recommendation'], 'rationale', colours))
    page.append(look.para(f'Your plan options will follow from {advisor(facts)}.', 'intro', colours))
    return [page]
