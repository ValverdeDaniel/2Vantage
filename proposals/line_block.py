"""One line of the proposal builder (plan.md §8.14; J30, J31, J47, J48, J52, J55, J56, J59–J62; the old
ProposalBuilder.jsx, ProposalPlansCard.jsx and EnrollmentStrip.jsx at 891f1b3, worked out on the server).

`block` gives the builder's line: its state and chips (J31), why it is off (J30), the kept line's incumbent (J47),
the EnrollmentStrip's people (J48), the recommendation (J52, J55; every recommended plan with its own change against
what it replaces), its words (J56), the section's parts, rows and card stats (J59, J61, J62), and how its pages read
(how many plans, how many pages). `facts` is the same line as the fact sheet `ready` and `checks` read. Every figure
is quotes' (`deal_state`'s results; rule 5); every name is the client's (`client_name` first, J14).
"""

from deals import lines
from intake import coverage as intent
from quotes import fields, presented, priced_kinds, split
from quotes import math as m
from quotes.math import enrollment as counts

from . import catalog, config, marks
from . import formatting as fmt
from . import page_columns as cols

CHIPS = {
    intent.PRESENTED: {
        'text': 'guaranteed',
        'tone': 'guaranteed',
        'title': 'Presented as in force — not marketed this year',
    },
    intent.GAP: {'text': 'new', 'tone': 'new', 'title': 'Proposed addition — not in force today'},
}
FUNDING = dict(lines.FUNDING)


def _replacing(plan, data, numbers, rows):
    """What a recommended plan answers for, in words: "Current 1", or the current plan's name on a line with one."""
    root = data.root(plan)
    bases = [root.id] if root.role == 'current' else data.base_ids(root)
    several = len(data.current) >= 2
    return [f'Current {numbers[pid]}' if several else cols.words(rows[pid]) for pid in bases]


def _picked(plan, kind, laid, state):
    data, results, rows = state.data, state.results, laid.rows
    monthly, _note = cols.premium(plan, results)
    return {
        'plan_id': plan.id,
        'kind': kind,
        'option': laid.options.get(plan.id),
        'words': cols.words(rows[plan.id]),
        'keep': kind == 'current',
        'monthly': monthly,
        'change': cols.change(plan, results),
        'replacing': _replacing(plan, data, laid.numbers, rows),
    }


def _renewals(laid, data):
    """On a line with several current plans, the renewal of each (its priced version when one is on), when every
    current plan has one on the proposal and some is not yet recommended: "Recommend the renewal for every plan"."""
    if len(data.current) < 2:
        return []
    picks = []
    for current in data.current:
        offers = [p for p in laid.shown if data.root(p).role == 'renewal' and data.root(p).renews == current.id]
        if not offers:
            return []
        picks.append(next((p for p in offers if p.version_of), offers[0]))
    return [p.id for p in picks if not p.recommended]


def _groups(data, laid, rows):
    """Per current plan, on a line with several: which recommended plans answer it."""
    if len(data.current) < 2:
        return []
    out = []
    for current in data.current:
        answers = [
            p.id
            for p in laid.shown
            if p.recommended and (p.id == current.id or current.id in data.base_ids(data.root(p)))
        ]
        out.append(
            {
                'current_id': current.id,
                'number': laid.numbers[current.id],
                'words': cols.words(rows[current.id]),
                'plan_ids': answers,
                'answered': bool(answers),
            }
        )
    return out


def recommendation(state, laid, kept):
    data, rows = state.data, laid.rows
    options = [p for p in laid.shown if p.role != 'current']
    picked = [_picked(p, cols.kind_of(p, data), laid, state) for p in laid.shown if p.recommended]
    return {
        'covered': state.recommendation['covered'],
        'missing': state.recommendation['missing'],
        'needs_pick': bool(options) and not kept,
        'plans': picked,
        'groups': _groups(data, laid, rows),
        'sold': [cols.words(rows[p.id]) for p in data.plans if p.sold],
        'renewals': _renewals(laid, data),
        'keepable': [c.id for c in data.current] if options and not kept else [],
    }


def _people_words(source):
    """The strip's words for where the line's people come from; counts typed on the current plans themselves read as
    theirs (quotes' 'typed' names one plan's own)."""
    if source == 'typed':
        return 'Typed for the current plans'
    return (m.SOURCES.get(source) or {}).get('label', 'Enrollment')


def enrollment(state):
    """The EnrollmentStrip (J48; OQ18): the line's people and where they come from, and whether the strip can type the
    line's figure (one current plan at most and no plan typed on its own, or a figure already stored, F88)."""
    data, results = state.data, state.results
    keys = m.enrollment_keys(data.rate_basis)
    found = m.people(data, results)
    figure = counts.figures_of(data.people.figure, keys) if data.people.on else None
    typed_plans = sum(1 for p in data.plans if m.typed(p, keys))
    source = found[1] if found else None
    return {
        'keys': keys,
        'figures': counts.as_plain(found[0]) if found else None,
        'source': source,
        'words': _people_words(source) if found else '',
        'typed': counts.as_plain(figure) if figure else None,
        'editable': (len(data.current) < 2 and not typed_plans) or figure is not None,
        'several': len(data.current) >= 2,
    }


def _row_choices(line):
    groups = {group: label for group, label, _keys in fields.groups_for(line)}
    return [
        {
            'key': key,
            'label': fields.BY_KEY[key]['label'],
            'group': fields.BY_KEY[key]['group'],
            'group_label': groups.get(fields.BY_KEY[key]['group'], ''),
        }
        for key in catalog.client_keys(line)
    ]


def section(line, spec):
    """The section's parts, rows and card stats (J59, J61, J62)."""
    picked = spec['card_stats']
    stats = picked or catalog.card_stats(line)
    return {
        'spec': spec,
        'rows': _row_choices(line),
        'card_stats': [{'key': key, 'label': catalog.stat_label(key)} for key in stats],
        'card_stats_standard': not picked,
        'preset': catalog.row_preset(line),
    }


def _blank_rows(line, spec, shown, rows):
    keys = spec['rows'] if spec['rows'] is not None else catalog.client_keys(line)
    out = []
    for key in keys:
        cells = [fmt.value(key, rows[p.id].values.get(key)) for p in shown]
        if spec['rows'] is None and not any(cells):
            continue
        if not all(cells):
            out.append(fields.BY_KEY[key]['label'])
    return out


def _unrated(state):
    data, results = state.data, state.results
    if data.rate_basis != 'composite':
        return 0
    keys = priced_kinds.premium_keys(data.rate_basis)
    return sum(
        1 for p in data.current if results[p.id]['monthly'] is None and not any(p.values.get(key) for key in keys)
    )


def facts(line, state, laid, ctx):
    """The fact sheet `ready` and `checks` read (no query)."""
    data, results = state.data, state.results
    spec, shown = ctx['spec'], laid.shown
    options = [p for p in shown if p.role != 'current']
    several = len(data.current) >= 2
    linked = {pid for p in options for pid in data.base_ids(data.root(p))}
    return {
        'line': line,
        'label': lines.label(line),
        'off': ctx['off'],
        'off_words': intent.OFF_LABELS.get(ctx['off'], '') if ctx['off'] else '',
        'kept': ctx['state'] == intent.PRESENTED,
        'options': len(options),
        'presented': len(shown),
        'starred': presented.has_stars(data),
        'several': several,
        'missing': state.recommendation['missing'],
        'sold': any(p.sold for p in data.plans),
        'composite': data.rate_basis == 'composite',
        'no_people': any(results[p.id]['reason'] == 'no_enrollment' for p in shown),
        'cost_or_pick': spec['parts']['cost'] or spec['parts']['recommendation'],
        'parts': spec['parts'],
        'priced': any(results[p.id]['monthly'] is not None for p in shown),
        'unrated': _unrated(state),
        'currents': len(data.current),
        'loose': sum(1 for p in options if p.starred and not data.base_ids(data.root(p))) if several else 0,
        'uncounted': [
            cols.words(laid.rows[p.id]) for p in data.current if p.id in linked and not results[p.id]['enrollment_used']
        ],
        'reasons': bool(config.get(ctx['config'], f'reasons.{line}')),
        'blank_rows': _blank_rows(line, spec, shown, laid.rows),
        # One plan filed as two, not yet printed as one column (D-219; slice 33): [(employee-only, dependents) names].
        'split': [(a.name, b.name) for a, b in split.unpaired(data, [p.id for p in shown])],
    }


def block(line, state, laid, ctx):
    """The builder's line. `ctx`: {config, marks, state (the intent's), off, spec, incumbent}."""
    data = state.data
    kept = ctx['state'] == intent.PRESENTED
    pages = laid.pages
    return {
        'line': line,
        'label': lines.label(line),
        'state': ctx['state'] or intent.SHOPPED,
        'chip': CHIPS.get(ctx['state']),
        'off': {'reason': ctx['off'], 'words': intent.OFF_LABELS[ctx['off']]} if ctx['off'] else None,
        'done': marks.line_done(ctx['marks'], line),
        'rate_basis': data.rate_basis,
        'currents': [
            {
                'id': p.id,
                'number': n,
                'words': cols.words(laid.rows[p.id]),
                'monthly': cols.premium(p, state.results)[0],
            }
            for n, p in enumerate(data.current, start=1)
        ],
        'incumbent': ctx['incumbent'] if kept else None,
        'quotes': sum(1 for p in data.plans if p.role != 'current'),
        'starred': sum(1 for p in data.plans if p.starred),
        'presented_ids': [p.id for p in laid.shown],
        'pages': len(pages),
        'room': presented.room(data),
        'recommendation': recommendation(state, laid, kept),
        'reasons': config.get(ctx['config'], f'reasons.{line}'),
        'enrollment': enrollment(state),
        **section(line, ctx['spec']),
    }


def incumbent(row):
    """A kept line's in-force facts from the intent's row (J47; the old incumbent card)."""
    if not row:
        return None
    return {
        'carrier': row['carrier'],
        'funding': FUNDING.get(row['funding'], ''),
        'rate_guarantee_through': row['rate_guarantee_through'],
        'renewal_date': row['renewal_date'],
    }
