"""Is this proposal ready for a client? (plan.md §5.4, §7.12; J28, J.5 B36; ported from old Vantage 891f1b3
`pipeline/proposal_ready.py`, D-175). Pure.

The firm is the client's representative, so nothing goes to a client without our recommendation on every marketed
line. One answer, read in three places: Issue refuses on it (slice 32), the builder's banner says it before the
click, and the checks list it (`no_recommendation`, a Stop).

What needs a pick, line by line (§5.4; quotes' `recommendation()` decides what covers a current plan):
- never a line off the proposal, nor one kept as-is (its current plan IS its recommendation; J52, B36);
- never a line with nothing but its current plans on it (nothing to choose; the old rule);
- never a line with a sold plan (the sold plan is the line's pick, as the old app read it);
- otherwise every current plan answered — recommended itself ("Keep this plan", OQ37), or renewed or replaced by a
  recommended plan; a line with no current plans needs one recommended plan.

Files not yet issued carry the Draft mark whatever this says (OQ35, default yes).
"""

DRAFT_MARK = 'Draft for review, not for clients'


def subjects(line):
    """What one line still needs, in words ("Medical", or "Medical, for Aetna PPO 2500" on a line with several current
    plans); [] when it needs nothing. `line`: {label, kept, off, options, sold, several, missing} — `missing` names
    the current plans quotes' `recommendation()` finds unanswered ('this line' when it has none)."""
    if line['off'] or line['kept'] or not line['options'] or line['sold']:
        return []
    if not line['missing']:
        return []
    if line['several']:
        return [f'{line["label"]}, for {words}' for words in line['missing']]
    return [line['label']]


def missing_by_line(lines):
    """{line key: [subjects]} for every line not ready, in the order given."""
    out = {}
    for line in lines:
        found = subjects(line)
        if found:
            out[line['line']] = found
    return out


def sentence(missing):
    """What Issue says instead (slice 32), and the builder's banner."""
    return (
        'A proposal always carries our recommendation. Pick a recommended plan before this goes to the client: '
        f'{"; ".join(missing)}.'
    )


def ready(lines):
    """{ok, missing: [subjects], sentence | None, draft}; not ok while no line is on the proposal."""
    missing = [subject for found in missing_by_line(lines).values() for subject in found]
    return {
        'ok': not missing and any(not line['off'] for line in lines),
        'missing': missing,
        'sentence': sentence(missing) if missing else None,
        'draft': DRAFT_MARK,
    }
