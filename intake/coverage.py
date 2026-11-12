"""Coverage and marketing intent (plan.md §5.2; B16–B21, B24). Pure: rows in, facts out.

Ported from old Vantage 891f1b3 `benefits/market/coverage.py`. Three facts per line, asked as two questions:
- *in force* and *on the proposal* live on the line's first `CurrentCoverage` row; *shopping* is
  `Deal.requested_lines`, written only through `services.set_intent` (B17);
- the card asks IN FORCE (yes or no) and THIS YEAR (Shop it, Keep as-is or Leave off), and `controls_to_intent`
  compiles them into the three stored facts, so the screen and the confirmation never disagree about a click.
A line with no row has never been answered: it is not "not in force" (the card asks instead).

Confirmation (B20) stores the decisions themselves, readable (`decisions`), instead of the old hash: the intent is
confirmed while today's decisions equal the stored ones, so any change shows "Changed since confirmed" with no hook on
any write path. A note, a carrier or a renewal date is not a decision; the rate guarantee is (the old hash's rule).

The old app gated `line_states` on the confirmation because legacy rows defaulted to "on the proposal"; 2Vantage has
no legacy rows, so the states read the intent as it stands (B24, Simplify).
"""

MARKET, KEEP, OFF = 'market', 'keep', 'off'
THIS_YEAR = (MARKET, KEEP, OFF)
# The card's column words are fixed; a line not in force reads the same choices as "Quote it" and "Present it".
THIS_YEAR_LABELS = {
    True: {MARKET: 'Shop it', KEEP: 'Keep as-is', OFF: 'Leave off'},
    False: {MARKET: 'Quote it', KEEP: 'Present it', OFF: 'Leave off'},
}

SHOPPED, PRESENTED, GAP, DORMANT = 'shopped', 'presented', 'gap', 'dormant'
STATE_LABELS = {
    SHOPPED: 'Marketed',
    PRESENTED: 'Presented as in force',
    GAP: 'Proposed addition',
    DORMANT: 'Not on this proposal',
}

LEFT_OFF, NOT_IN_INTENT = 'left_off', 'not_in_intent'
OFF_LABELS = {
    LEFT_OFF: 'Left off in Coverage & marketing intent',
    NOT_IN_INTENT: 'Not in the Coverage & marketing intent',
}

# The documents each line needs while it is in force and shopped, in the card's order (B21).
DOC_KINDS = ('renewal', 'invoice', 'sbc')
DOC_LABELS = {'renewal': 'Renewal', 'invoice': 'Invoice', 'sbc': 'SBC'}

# In-force commission source (§4.6; B14). Blank = unknown.
COMMISSION_SOURCES = [
    ('client', 'Client told us'),
    ('carrier', 'Carrier told us'),
    ('aor_letter', 'From the AOR letter'),
]
COMMISSION_SOURCE_KEYS = {key for key, _ in COMMISSION_SOURCES}


def this_year_of(shopping, on_proposal):
    """The THIS YEAR choice a stored (shopping, on_proposal) pair reads as; shopping is the louder fact."""
    if shopping:
        return MARKET
    return KEEP if on_proposal else OFF


def this_year_label(in_force, this_year):
    return THIS_YEAR_LABELS[bool(in_force)].get(this_year, '')


def controls_to_intent(has_today, this_year):
    """(in_force, shopping, on_proposal) from the card's two controls: the one place the collapse is defined."""
    return bool(has_today), this_year == MARKET, this_year in (MARKET, KEEP)


def line_state(in_force, shopping, on_proposal):
    """One line's state from its three facts: not in force is a gap even when shopped; then shopped, presented."""
    if not in_force:
        return GAP
    if shopping:
        return SHOPPED
    return PRESENTED if on_proposal else DORMANT


def first_rows(coverage):
    """{line: its first row} — the row the card shows and decides on. `coverage` is in sort order."""
    by_line = {}
    for row in coverage:
        by_line.setdefault(row.line, row)
    return by_line


def intent_rows(line_keys, requested, coverage):
    """One row per line with coverage or requested, in `line_keys` order (canonical, §4.1): the card's matrix."""
    by_line = first_rows(coverage)
    wanted = set(requested or [])
    rows = []
    for key in line_keys:
        row = by_line.get(key)
        if row is None and key not in wanted:
            continue
        shopping = key in wanted
        in_force = bool(row.in_force) if row else False
        on_proposal = bool(row.on_proposal) if row else True
        year = this_year_of(shopping, on_proposal)
        state = line_state(in_force, shopping, on_proposal) if row else ''
        rows.append(
            {
                'line': key,
                'coverage_id': row.id if row else None,
                'answered': row is not None,
                'in_force': in_force,
                'shopping': shopping,
                'on_proposal': on_proposal,
                'this_year': year,
                'this_year_label': this_year_label(in_force, year),
                'state': state,
                'state_label': STATE_LABELS.get(state, ''),
                'rate_guarantee_through': _iso(row.rate_guarantee_through) if row else None,
                'carrier': row.carrier if row else '',
                'funding': row.funding if row else '',
                'renewal_date': _iso(row.renewal_date) if row else None,
                'notes': row.notes if row else '',
            }
        )
    return rows


def _iso(value):
    return value.isoformat() if hasattr(value, 'isoformat') else value


def decisions(rows):
    """The decisions a confirmation stores and compares, readable: {line: {in_force, this_year,
    rate_guarantee_through}}; `in_force` is None on a line nobody has answered."""
    return {
        row['line']: {
            'in_force': row['in_force'] if row['answered'] else None,
            'this_year': row['this_year'],
            'rate_guarantee_through': row['rate_guarantee_through'],
        }
        for row in rows
    }


def confirmation(confirmed, rows):
    """'done' (confirmed and unchanged), 'stale' (confirmed once, changed since) or 'open' (never confirmed)."""
    if not confirmed or 'decisions' not in confirmed:
        return 'open'
    return 'done' if confirmed['decisions'] == decisions(rows) else 'stale'


def line_states(rows, quote_lines):
    """{line: state} for every line in the intent plus every line holding plans (`quote_lines`, quotes' provider).
    A line that only holds plans, or that nobody has answered, reads as shopped: unknown is never a gap sell."""
    states = {line: SHOPPED for line in quote_lines}
    for row in rows:
        states[row['line']] = row['state'] or SHOPPED
    return states


def lines_off(rows, quote_lines, recorded):
    """{line: reason} for the lines holding plans that stay off the client's documents (B24; F13, J2):
    `left_off` when the intent says Leave off; `not_in_intent` when the intent never names a line that holds plans,
    once an intent is recorded (lines requested, or a confirmation). Never a line with a sold plan."""
    by_line = {row['line']: row for row in rows}
    off = {}
    for line, facts in quote_lines.items():
        if facts.get('sold'):
            continue
        row = by_line.get(line)
        if row is None:
            if recorded:
                off[line] = NOT_IN_INTENT
        elif row['answered'] and row['this_year'] == OFF:
            off[line] = LEFT_OFF
    return off


def needs_documents(in_force, this_year):
    """Whether a line's missing renewal, invoice and SBC count as gaps: only when in force and shopped (B21)."""
    return bool(in_force) and this_year == MARKET


def documents_by_line(documents, line_keys):
    """{line: {kind: [document ids]}} for the card's chips. `documents` are (id, kind, lines) triples. A file with no
    lines counts for every line ("nobody said"); a file scoped to other lines counts for none of these."""
    out = {line: {} for line in line_keys}
    for doc_id, kind, doc_lines in documents:
        if kind not in DOC_KINDS:
            continue
        targets = [line for line in doc_lines if line in out] if doc_lines else list(out)
        for line in targets:
            out[line].setdefault(kind, []).append(doc_id)
    return out


def counts(rows):
    """The footer's tally and the header badge's gaps (B20)."""
    return {
        'in_force': sum(1 for r in rows if r['in_force']),
        'shopping': sum(1 for r in rows if r['shopping']),
        'proposal': sum(1 for r in rows if r['on_proposal']),
        'keep': sum(1 for r in rows if r['this_year'] == KEEP and r['in_force']),
        'new': sum(1 for r in rows if r['answered'] and not r['in_force'] and r['this_year'] != OFF),
        'unanswered': sum(1 for r in rows if not r['answered']),
    }


def meta():
    """`/api/meta/`'s `intake.coverage`: the card's words (B16–B21)."""
    return {
        'this_year': [
            {'key': key, 'label': THIS_YEAR_LABELS[True][key], 'gap_label': THIS_YEAR_LABELS[False][key]}
            for key in THIS_YEAR
        ],
        'states': [{'key': key, 'label': label} for key, label in STATE_LABELS.items()],
        'off_reasons': [{'key': key, 'label': label} for key, label in OFF_LABELS.items()],
        'documents': [{'kind': kind, 'label': DOC_LABELS[kind]} for kind in DOC_KINDS],
        'commission_sources': [{'key': key, 'label': label} for key, label in COMMISSION_SOURCES],
    }
