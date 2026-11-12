"""One line of the client deck's Facts (plan.md §9.5; J.4, J.6.3): client-shaped, built from what the builder has
already worked out (quotes' `deal_state` for the line, `line_layout.lay_out`, the line's settings). Pure.

Only what a client file may print enters (J.4 "never", ch29): a plan's client fields (§4.3 `client`, so never
`sl_lasers`), its identity and the client's name for it (J14), its option number as Issue will stamp it, and quotes'
figures for it (rule 5). Never `star_reason`, internal notes, sources, document names, review marks or commission.

A plan: {id, kind (current | renewal | option | priced), current, number, option, carrier, name, words, priced_label,
values, sbc, recommended, sold, monthly, annual, change {delta (a year), pct}, part_of, bases, credit, counts,
employee, first {monthly, annual, rates}, item (an object with `values`, for the house rows)}.
"""

from types import SimpleNamespace

from deals import lines as vocab
from quotes import fields
from quotes import math as m

from .. import page_columns as cols
from ..why import why_for

RATE_KEYS = (*fields.TIER_RATE_KEYS, 'unit_rate')
TIER_WORDS = {'EE': 'Employee only', 'ES': 'Employee + spouse', 'EC': 'Employee + child(ren)', 'FAM': 'Family'}
TYPED_SOURCES = ('typed', 'from current plan', 'from replaced plan', 'from original plan', 'line')


def _client_values(values):
    return {key: raw for key, raw in (values or {}).items() if fields.BY_KEY.get(key, {}).get('client')}


def _valued(rows):
    """The client fields any plan of the line holds a value for (the RAW text, so a stored '0' counts): what the old
    payload offered as the line's rows when the producer keeps every row (its any-value filter, 891f1b3)."""
    found = set()
    for row in rows:
        found.update(key for key, raw in _client_values(row.values).items() if str('' if raw is None else raw).strip())
    return sorted(found)


def _sbc(values):
    """The SBC link a client file may carry: an http(s) address, one token, ≤255 characters; else ''."""
    found = str(values.get('sbc_url') or '').strip()
    ok = found.lower().startswith(('https://', 'http://')) and len(found) <= 255
    return found if ok and not any(ch.isspace() or ch == '"' for ch in found) else ''


def _first(plan, data, results):
    """What the carrier first offered, for a priced version of an offer (never of an in-force plan): its original's
    price and rates (the "What we negotiated" and "first renewal offer" pages; D-178)."""
    root = data.root(plan)
    if root.id == plan.id or root.role == 'current':
        return None
    found = results[root.id]
    rates = {key: root.values.get(key) for key in RATE_KEYS if root.values.get(key) not in (None, '')}
    return {'id': root.id, 'monthly': found['monthly'], 'annual': found['annual'], 'rates': rates}


def plan(row, plan_data, state, laid):
    data, results = state.data, state.results
    result = results[plan_data.id]
    kind = cols.kind_of(plan_data, data)
    values = _client_values(row.values)
    employee = m.employee_cost(plan_data)
    return {
        'id': row.id,
        'kind': kind,
        'current': plan_data.role == 'current',
        'number': laid.numbers.get(row.id),
        'option': laid.options.get(row.id),
        'carrier': row.carrier or '',
        'name': row.client_name or row.name or '',
        'words': cols.words(row),
        'priced_label': ((row.derived or {}).get('label') or 'Priced version') if kind == 'priced' else '',
        'values': values,
        'sbc': _sbc(values),
        'recommended': plan_data.recommended,
        'sold': plan_data.sold,
        'monthly': result['monthly'],
        'annual': result['annual'],
        'change': result['change'],
        'part_of': result['part_of'],
        'bases': list(result['base_ids']),
        'credit': result.get('credit'),
        'counts': result['enrollment_used'],
        'source': result['enrollment_source'],
        'employee': employee if any(v is not None for v in employee.values()) else None,
        'first': _first(plan_data, data, results),
        'item': SimpleNamespace(values=values),
    }


def basis(state, shown):
    """The words under a priced table: whose enrollment priced it ("24 × Employee only · 6 × Employee + spouse
    (expected)"), and how many plans are priced on counts typed for that plan; '' when neither (the builder says when
    nothing is counted, never the client). On a line with several current plans the line's tally is nobody's: only
    the typed plans are named (old `proposal_pdf._basis`)."""
    data, results = state.data, state.results
    typed = sum(1 for p in shown if results[p.id]['enrollment_source'] == 'typed')
    note = f'{typed} plan{"s" if typed != 1 else ""} on expected enrollment entered for that plan' if typed else ''
    found = m.people(data, results)
    text = ''
    if found and data.rate_basis == 'composite' and len(data.current) < 2:
        figures, source = found
        shown_tiers = [f'{m.plain(figures[tier])} × {TIER_WORDS[tier]}' for tier in TIER_WORDS if figures.get(tier)]
        text = ' · '.join(shown_tiers)
        if text and source in TYPED_SOURCES:
            text = f'{text} (expected)'
    return '; '.join(part for part in (text, note) if part)


def groups(data, shown_ids, picks):
    """[(current plan id, [the recommended plans answering it])] on a line with several current plans, in the
    current plans' order; a current plan recommended itself answers itself ("Keep this plan")."""
    out = []
    for current in data.current:
        answers = [pid for pid in picks if pid == current.id or current.id in data.base_ids(data.root(data.by_id[pid]))]
        if answers:
            out.append((current.id, [pid for pid in shown_ids if pid in answers]))
    return out


def line(key, state, laid, ctx):
    """The line's Facts. `ctx`: {config (stored), spec (line_spec), intent (state), incumbent, guarantee}."""
    data = state.data
    rows = laid.rows
    shown = laid.shown
    plans = {p.id: plan(rows[p.id], p, state, laid) for p in shown}
    sold = [p.id for p in shown if p.sold]
    picks = sold or [p.id for p in shown if p.recommended]
    spec = ctx['spec']
    return {
        'key': key,
        'label': vocab.label(key),
        'state': ctx['intent'] or 'shopped',
        'field_set': vocab.BY_KEY[key]['field_set'],
        'rate_basis': data.rate_basis,
        'several': len(data.current) >= 2,
        'parts': spec['parts'],
        'rows': spec['rows'],
        'valued': _valued(rows.values()),
        'card_stats': spec['card_stats'],
        'table_note': spec['table_note'],
        'reasons': why_for(ctx['config'], key),
        'incumbent': ctx['incumbent'],
        'guarantee': ctx['guarantee'],
        'plans': plans,
        'order': [p.id for p in shown],
        'pages': laid.pages,
        'picks': picks,
        'groups': groups(data, [p.id for p in shown], picks) if len(data.current) >= 2 else [],
        'basis': basis(state, shown),
        'packages': state.packages,
    }
