"""Printed tier counts and unrequested lines in a quote read's change set (plan.md §5.5, §10.4; D56, D67, OQ30;
O.6 #10). Nothing is written here.

- **Counts** (OQ30, default yes): with no census on the line, the tier counts a file prints are proposed, unticked —
  per current plan when printed per plan (they land as that plan's typed counts through `set_enrollment(plans=…)`,
  which a second current plan needs, F88), or as the line's figure when printed for the whole line. They are never a
  plan's own enrollment until a person ticks them. With a census on the line they are not proposed: the census prices
  the line (D67 ranks printed counts below it), and a finding says so. Counts the plan (or the line) already holds
  are not proposed again (D60), so a re-read of a file whose counts were used proposes none.
- **Lines** (D56): every printed line is read; lines the deal does not ask for become one `add_lines` item, ticked
  only when the deal asks for no line yet (it lands through Intake's intent service, slice 19).
"""

from deals import lines as line_vocab

from ..selectors import people as people_selector
from .schema import TIERS

CHECK = 'Printed in the file: check them before using them. They price the plan only once ticked.'
LINE_FIGURE = 'Printed for the whole line: they would become the line’s typed counts.'


def _text(counts):
    return ' · '.join(f'{counts[tier]} {tier}' for tier in TIERS if tier in counts)


def _same(held, counts):
    """The stored counts are these (a tier left out is none)."""
    return {tier: held.get(tier) or 0 for tier in TIERS} == {tier: counts.get(tier) or 0 for tier in TIERS}


def _composite(line):
    return (line_vocab.BY_KEY.get(line) or {}).get('rate_basis') == 'composite'


def add(builder, deal, merged, lines):
    people = people_selector.load(deal.id, lines) if lines else {}
    for line in lines:
        if not _composite(line):
            continue
        census = bool(people.get(line) and people[line].census)
        printed = [
            found
            for found in merged['plans']
            if found['line'] == line and found['side'] == 'current' and any(tier in found['counts'] for tier in TIERS)
        ]
        whole = merged['line_counts'].get(line)
        if census and (printed or whole):
            builder.findings.append(
                {
                    'text': f'The file prints tier counts for {line_vocab.BY_KEY[line]["label"]}; the census already '
                    'prices this line, so they are not proposed.',
                    'hard': False,
                }
            )
            continue
        for found in printed:
            item = builder.by_key.get(found['key'])
            if item is None:
                continue
            counts = {tier: found['counts'][tier] for tier in TIERS if tier in found['counts']}
            held = next((plan.enrollment for plan in builder.plans if plan.id == item['plan']), None)
            if held and _same(held, counts):
                continue
            target = {'plan': item['plan']} if item['plan'] else {'item': item['id']}
            builder.items.append(
                {
                    'id': builder.next_id(),
                    'op': 'summary_counts',
                    'line': line,
                    'for': target,
                    'label': f'{item["carrier"]} {item["name"]}',
                    'counts': counts,
                    'text': _text(counts),
                    'doc': found['counts'].get('_doc'),
                    'page': found['counts'].get('_page'),
                    'tick': False,
                    'stale': False,
                    'why': CHECK,
                }
            )
        if whole and not printed:
            counts = {tier: whole['counts'][tier] for tier in TIERS if tier in whole['counts']}
            if people.get(line) and _same(people[line].figure, counts):
                continue
            builder.items.append(
                {
                    'id': builder.next_id(),
                    'op': 'summary_counts',
                    'line': line,
                    'for': None,
                    'label': line_vocab.BY_KEY[line]['label'],
                    'counts': counts,
                    'text': _text(counts),
                    'doc': whole.get('doc'),
                    'page': whole.get('page'),
                    'tick': False,
                    'stale': False,
                    'why': LINE_FIGURE,
                }
            )
    asked = list(deal.requested_lines or [])
    extra = [line for line in lines if line not in asked]
    if extra:
        names = ', '.join(line_vocab.BY_KEY[line]['label'] for line in extra if line in line_vocab.BY_KEY)
        builder.items.append(
            {
                'id': builder.next_id(),
                'op': 'add_lines',
                'lines': extra,
                'label': names,
                'tick': not asked,
                'stale': False,
                'why': 'The deal asks for no line yet.'
                if not asked
                else 'The file quotes lines the deal does not ask for.',
            }
        )
