"""The answer's figures: the program at a glance and what negotiating saved (plan.md §9.5; J126–J128; old Vantage
891f1b3 `exec_summary.at_a_glance`, `_glance_row`, `presentation_model.negotiated`). Pure.

Over the summary's line facts (`summary_read.line_facts`), so the overview's figures and the executive summary's can
never part. Every sum and change is quotes' (`quotes.math`; rule 5), and the total refuses rather than half-adds
(`summary_blocks.deal.totals`): a line with two picks for one current plan (2V allows several, J165) prints a row for
each, each against what it replaces, and no total.

A row: {line, label, plan_id, name, replacing, today, recommended, delta, pct, kept}; annual figures.
"""

from quotes import math as m

from ..summary_blocks import deal as deal_totals
from ..summary_blocks import reading as r


def _row(line, base, plan, several):
    kept = plan is not None and base is not None and plan['id'] == base['id']
    today = base['annual'] if base else None
    now = plan['annual'] if plan else None
    delta = pct = None
    if kept:
        delta, pct = 0, 0.0
    elif plan and plan['change']:
        delta, pct = plan['change']['delta'], plan['change']['pct']
    # The summary's name for a plan, carrier first ("Aetna · HMO 1000"; old `exec_summary._plan_name`, D-175).
    name = plan['words'] if plan else ''
    return {
        'line': line['key'],
        'label': line['label'],
        'plan_id': plan['id'] if plan else None,
        'name': f'Keep {name}' if kept else name,
        'replacing': base['words'] if several and base else '',
        'today': today,
        'recommended': now,
        'delta': delta,
        'pct': pct,
        'kept': kept,
    }


def _several(line):
    """(rows, anything picked) on a line with several current plans: each current plan with each plan answering it,
    or as it is when nothing is linked to it."""
    rows, picked = [], False
    for base in line['currents']:
        answers = [p for p in line['picks'] if p['id'] == base['id'] or base['id'] in p['bases']]
        if not answers and not any(base['id'] in p['bases'] for p in line['options']):
            answers = [base]
        for plan in answers:
            rows.append(_row(line, base, plan, True))
            picked = picked or plan['id'] != base['id']
    return rows, picked


def rows(lines):
    """The at-a-glance rows, or None until anything is recommended (a deal still being built prints no overview)."""
    out, picked = [], False
    for line in lines:
        if r.several(line):
            found, any_pick = _several(line)
            out += found
            picked = picked or any_pick
            continue
        current = r.current(line)
        picks = list(line['picks'])
        picked = picked or bool(picks)
        if not picks and line['state'] == 'presented' and current:
            picks = [current]  # a line kept as it is keeps its plan: that IS its recommendation
        if current is None and not picks:
            continue
        out += [_row(line, current, plan, False) for plan in picks or [None]]
    return out if picked else None


def total(lines):
    """{today, recommended, delta, pct, credit} across the lines, or None when the total would not be honest."""
    try:
        found = deal_totals.totals({'lines': lines})
    except r.Refused:
        return None
    change = m.change(found['now_annual'], found['was_annual'])
    return {
        'today': found['was_annual'],
        'recommended': found['now_annual'],
        'delta': change['delta'] if change else None,
        'pct': change['pct'] if change else None,
        'credit': found['credit'],
    }


def negotiated(glance, plans_by_id):
    """What negotiating saved, line by line: the carrier's first figure beside the one we recommend, both against
    today. Only a line where a recommended plan began as a higher offer (a priced version of a quote) or carries a
    first-year credit. [{line, label, first_pct, final_pct, saved, first_annual, final_annual, today_annual}]"""
    by_line = {}
    for row in glance or []:
        by_line.setdefault(row['line'], []).append(row)
    out = []
    for line, found in by_line.items():
        if any(row['today'] is None or row['recommended'] is None for row in found):
            continue
        today = m.add([row['today'] for row in found])
        if not today:
            continue
        first, final, moved = [], [], False
        for row in found:
            plan = plans_by_id.get(row['plan_id']) or {}
            credit = ((plan.get('credit') or {}).get('annual') or 0) if not row['kept'] else 0
            net = m.add([row['recommended'], -credit])
            final.append(net)
            offer = plan.get('first') if not row['kept'] else None
            if offer and offer.get('annual') is not None:
                first.append(offer['annual'])
                moved = True
            elif credit:
                first.append(row['recommended'])
                moved = True
            else:
                first.append(net)
        first_total, final_total = m.add(first), m.add(final)
        if not moved or first_total is None or final_total is None or first_total <= final_total:
            continue
        out.append(
            {
                'line': line,
                'label': found[0]['label'],
                'first_pct': (m.change(first_total, today) or {}).get('pct'),
                'final_pct': (m.change(final_total, today) or {}).get('pct'),
                'saved': m.add([first_total, -final_total]),
                'first_annual': first_total,
                'final_annual': final_total,
                'today_annual': today,
            }
        )
    return out
