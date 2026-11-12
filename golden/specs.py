"""The golden specs and their answer keys, read from JSON (plan.md §12.6, Q.4, Q.5).

A spec (`specs/gdN.json`) is the one description of a golden deal. `seed.py` builds it in 2Vantage, and
`tools/parity/old_loader.py` reads the same file into old Vantage through its parity profile. Synthetic data only.

    key             "GD1": the deal's name in the plan, the keys and the parity harness
    about           what the deal proves, in words
    client          the client's name; the seed replaces any client of this name
    status          the client's status (§5.1): prospect, new_client (made by Convert to client) or existing_client
    effective_date  ISO date
    lines           the requested lines, in any order (the deal keeps §4.1's)
    intake          optional: {answers: {question key: raw text}}, typed through intake's one writer (slice 39)
    plans           in creation order; each:
        ref         the plan's name in the keys and in other plans' links ("A", "CG1N")
        line, role, carrier, name
        links       refs of current plans: a renewal's one current plan, or the plans an alternate replaces
        copy_of     optional: a Duplicate of that ref (`copy_plan`, rates kept), named `name`, then given `values`
        values      {field key: raw text}, as a person types them (quotes/fields.py)
        enrollment  optional: typed counts by tier, e.g. {"EE": 10, "ES": 3, "EC": 2, "FAM": 5}, switched on
    starred, recommended    refs
    packages        [{line, name, plans: [refs]}]: member-built packages
    reasons         {line: the proposal's reason}
    parity          the parity profile: how the deal maps onto old Vantage's records (below)

The parity profile (Q.5) says what the old app (commit `old_app`) cannot express and how the rest maps:
    case                the old BenefitsCase's own fields beyond name, renewal date and lines (e.g. its stage)
    client_book         null: a Prospect, a deal not on the old client book (§13.4); later {"type": "new"|"existing"}
    values_layer        "edited": values land as the old hand edit does (edited_value over an empty read value)
    values_left_out     {field key: why}: keys the old plan has no row for
    intake_layer        "edited": intake answers land as the old form's hand edit does (CaseField.edited_value)
    intake_left_out     {question key: why}: answers the old form cannot hold
    links               {ref: current ref}: the one current plan an old option compares with (Plan.compares_to),
                        where the 2V links do not name exactly one; a renewal always maps to renewal_of
    copies              {ref: "duplicate"}: made with the old Duplicate (duplicate_of) and its values set
    recommended_by_current  {line: {current ref: ref}}: one pick per current plan on a line with several
    recommended_by_line     {line: ref}: the pick on a line with one current plan
    line_counts         {line: ref}: on a line with one current plan, that plan's typed counts also become the old
                        line's counts (proposal_config.tier_counts_by_line), which price the line's unlinked options
    figures_left_out    {ref: why}: key figures the old app cannot reproduce because of what is left out
    left_out            [{what, why}]: everything else the old app cannot hold, in words

An answer key (`keys/gdN.json`) carries `checked_by`, `checked_on` and `method` (null until Stephanie signs it)
beside the figures, and changes only with her agreement.
"""

import json
from functools import cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC_DIR = HERE / 'specs'
KEY_DIR = HERE / 'keys'


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


@cache
def _all():
    specs = [_read(path) for path in sorted(SPEC_DIR.glob('gd*.json'))]
    return {spec['key']: spec for spec in specs}


def keys():
    """The golden deals' keys, in order: ['GD1', 'GD2', …]."""
    return list(_all())


def load(key):
    """One spec, as a fresh dict (callers may change their copy)."""
    return json.loads(json.dumps(_all()[key]))


def load_all():
    return [load(key) for key in keys()]


def answer_key(key):
    """The answer key of one deal (Q.4)."""
    return _read(KEY_DIR / f'{key.lower()}.json')
