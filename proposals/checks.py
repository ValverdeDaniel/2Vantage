"""Before you export: what would print wrong (plan.md §8.14; J23; ported from old Vantage 891f1b3
`pipeline/proposal_checks.py`, the 2026-10-22 call). Pure.

It warns and blocks nothing itself: the one item that is also a door's guard is a marketed line with no
recommendation, which Issue refuses on (`ready`). Each item is {code, level, line, line_label, text, fix}: `level` is
`stop` (the document will refuse or come out empty), `warn` (it will print, wrongly or blank) or `info`; `fix` names
the builder card that fixes it ({card}) or a deal tab ({tab}). Most serious first.

The checks read one fact sheet per line, which `builder` builds from quotes' `deal_state` and intake's intent (no
query here). Built in slice 25: nothing_presented, line_off, oversize, unstarred, no_enrollment, no_prices,
current_unrated, not_linked, link_needs_enrollment, no_recommendation, no_reasons, missing_values. With their cards:
no_next_steps, summary_counts_hidden_carriers, medicare_not_shown (slice 26), split_plan (slice 33); history_unfigured
waits for past plan years (J44, deferred); demo_firm_pages is dropped (J23).
"""

from . import ready as gate

UNSTARRED_WARN_AT = 8  # nothing starred and more quotes than this: every one prints
NAMED_ROWS = 3
LEVELS = {'stop': 0, 'warn': 1, 'info': 2}


def oversize_sentence(label, count, cap):
    """The one sentence for a line presenting more plans than a client page holds (the files' refusal says the same)."""
    return (
        f'{label} has {count} plans on the proposal; a client page holds at most {cap} on a line. '
        f'Star the plans to present on {label} first.'
    )


def _item(code, level, text, line=None, card=None, tab=None):
    fix = {'card': card} if card else {'tab': tab} if tab else None
    return {
        'code': code,
        'level': level,
        'line': line['line'] if line else '',
        'line_label': line['label'] if line else '',
        'text': text,
        'fix': fix,
    }


def _plural(count, one, many):
    return one if count == 1 else many


def _enrollment(line):
    label = line['label']
    if line['composite'] and line['options'] and line['no_people'] and line['cost_or_pick']:
        return _item(
            'no_enrollment',
            'warn',
            f'No enrollment on {label}: its monthly totals, cost summary and recommendation print blank. Enter the '
            'expected enrollment on its Plans card, or add the census.',
            line,
            card='quotes',
        )
    if line['parts']['cost'] and line['presented'] and not line['priced']:
        return _item(
            'no_prices',
            'warn',
            f'{label} has no prices yet, so its cost summary will not print. Check its rates and enrollment.',
            line,
            card='quotes',
        )
    return None


def _currents(line):
    label, out = line['label'], []
    unrated, currents = line['unrated'], line['currents']
    if unrated and line['options'] and line['parts']['cost'] and line['priced']:
        out.append(
            _item(
                'current_unrated',
                'warn',
                f'{unrated} of {currents} current plan{_plural(currents, "", "s")} on {label} '
                f'{_plural(unrated, "has", "have")} no rates, so what the client pays today and the change from it '
                "print blank. A renewal package often prints only next year's rates: add last year's renewal or an "
                "invoice on the Documents tab, or type today's rates on the Advisor.",
                line,
                tab='documents',
            )
        )
    if line['several'] and line['loose']:
        loose = line['loose']
        out.append(
            _item(
                'not_linked',
                'warn',
                f'{label} has {currents} current plans, and {loose} starred plan{_plural(loose, " is", "s are")} not '
                f'linked to one, so {_plural(loose, "it prints", "they print")} under Other options. Pick what each '
                'one replaces under "Replacing:".',
                line,
                card='quotes',
            )
        )
    if line['several'] and line['uncounted']:
        out.append(
            _item(
                'link_needs_enrollment',
                'warn',
                f"{label}: enter each current plan's enrollment, or the options linked to {line['uncounted'][0]} print "
                'with no change in cost and the renewal page prints no total.',
                line,
                card='quotes',
            )
        )
    return out


def _recommendation(line, any_reasons, deal_words):
    found = gate.subjects(line)
    if found:
        return _item(
            'no_recommendation',
            'stop',
            f'{"; ".join(found)}: no recommended plan yet, so the proposal cannot be issued and drafts print a '
            'Draft mark.',
            line,
            card='quotes',
        )
    has_words = line['reasons'] or (not any_reasons and deal_words)
    if line['options'] and not line['kept'] and line['parts']['recommendation'] and not has_words:
        return _item(
            'no_reasons',
            'warn',
            f'{line["label"]} has a recommendation but no reasons: say why in a sentence or two, because the client '
            'will ask.',
            line,
            card='quotes',
        )
    return None


def _blank_rows(line):
    rows = line['blank_rows']
    if not (line['parts']['comparison'] and line['presented'] and rows):
        return None
    named = ', '.join(rows[:NAMED_ROWS])
    more = len(rows) - NAMED_ROWS
    return _item(
        'missing_values',
        'warn',
        f'{line["label"]}: {len(rows)} benefit row{_plural(len(rows), "", "s")} print blank for some plans '
        f'({named}{f", and {more} more" if more > 0 else ""}).',
        line,
        card='rows',
    )


def _line_checks(line, cap, any_reasons, deal_words):
    label = line['label']
    if line['off']:
        return [
            _item(
                'line_off',
                'warn',
                f'{label} has quotes but is off the proposal ({line["off_words"].lower()}): no client document will '
                'show it.',
                line,
                tab='intake',  # the intent card, until the builder mounts it (J46, slice 26)
            )
        ]
    out = []
    if line['presented'] > cap:
        out.append(_item('oversize', 'stop', oversize_sentence(label, line['presented'], cap), line, card='quotes'))
    elif line['options'] > UNSTARRED_WARN_AT and not line['starred']:
        out.append(
            _item(
                'unstarred',
                'warn',
                f'Nothing is starred on {label}, so all {line["options"]} quotes go on the proposal. Star the ones to '
                'present.',
                line,
                card='quotes',
            )
        )
    out.extend(item for item in (_enrollment(line), *_currents(line)) if item)
    out.extend(item for item in (_recommendation(line, any_reasons, deal_words), _blank_rows(line)) if item)
    return out


def checks(lines, *, cap, deal_words=''):
    """The list for the builder's lines (fact sheets, in the builder's order), most serious first."""
    items = []
    if not any(not line['off'] for line in lines):
        items.append(
            _item(
                'nothing_presented',
                'stop',
                'No line of coverage is on the proposal. Check the Coverage & marketing intent.',
                tab='intake',
            )
        )
    any_reasons = any(line['reasons'] for line in lines)
    for line in lines:
        items.extend(_line_checks(line, cap, any_reasons, (deal_words or '').strip()))
    return sorted(items, key=lambda item: LEVELS[item['level']])
