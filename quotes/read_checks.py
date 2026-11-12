"""Checks on what Claude proposes for the plan table, in code, before anyone sees it (plan.md §10.4; D88, D76; the old
benefits/ai/plan_checks.py `verify` at 891f1b3, restated over a change set). No AI, no cost, nothing written.

`for_read(items, plans)` checks a quote read's change set; `for_values(plan, values)` one plan a chat turn edits.
Each finding is {text, hard, kind}, naming the plan and the field, never a file's words. **Hard** findings are facts
code is sure of, which step a whole read up to Opus 5.5 for an admin or a direct person (D76, `ai.reading.steps_up`):
- `absent_rate`: a tier rate the read proposes is printed nowhere in its file (unless the file has image pages,
  where it may be printed out of the text's sight);
- `no_rates`: a plan the read makes on a tier-rated line comes with no monthly rates and no quoted premium;
- `shared_code`: two plans of one line and role in the read share a carrier code: one plan read twice;
- `unpaired`: a read that has renewals on a line leaves one of that line's current plans without its renewal.
**Soft** findings are listed for the person, never a reason to read again: values not found in their file (one line
for all of them), tier rates out of order, and printed counts times the rates that miss the premium the file prints
(the old premium reconciliation, D88's "with printed counts", priced by quotes/math).
"""

from types import SimpleNamespace

from ai import codes as plan_codes
from deals import lines
from documents.locate import query as located

from . import fields
from . import math as m

HARD = frozenset({'absent_rate', 'no_rates', 'shared_code', 'unpaired'})
PLAN_OPS = ('create_plan', 'set_values', 'pick_current')
RATES = fields.TIER_RATE_KEYS
PREMIUM = 'group_premium_monthly'
TIERS = m.TIERS
TOLERANCE = 1  # dollars a month: the carriers' own rounding


def _finding(text, kind):
    return {'text': text, 'hard': kind in HARD, 'kind': kind}


def _label(item):
    role = {'alternate': 'quote'}.get(item.get('role'), item.get('role') or 'plan')
    return f'{item.get("carrier", "")} {item.get("name", "")} ({role})'.strip()


def _composite(line):
    return (lines.BY_KEY.get(line) or {}).get('rate_basis') == 'composite'


def _values(item, plans):
    held = dict(plans[item['plan']].values or {}) if item.get('plan') in plans else {}
    held.update(
        {value['key']: value['new'] for value in item.get('values') or [] if value.get('new') not in (None, '')}
    )
    return held


def tier_order(label, values):
    """Soft findings for tier rates out of order: EE+Spouse and EE+Child(ren) above EE, Family the highest."""
    rate = {key: m.decimal(values.get(key)) for key in RATES}
    ee, es, ec, fam = (rate[key] for key in RATES)
    out = []
    if ee and es and es <= ee:
        out.append(_finding(f'{label}: EE + Spouse is not above EE', 'tier_order'))
    if ee and ec and ec <= ee:
        out.append(_finding(f'{label}: EE + Child(ren) is not above EE', 'tier_order'))
    if fam and any(x and x > fam for x in (ee, es, ec)):
        out.append(_finding(f'{label}: Family is not the highest rate', 'tier_order'))
    return out


def _absent(item, out):
    """Hard for each tier rate printed nowhere; the count of other values not found."""
    others = 0
    for value in item.get('values') or []:
        loc = value.get('loc') or {}
        if loc.get('state') != located.ABSENT:
            continue
        if value['key'] in RATES and loc.get('why') != 'image_pages':
            label = fields.BY_KEY[value['key']]['label']
            out.append(_finding(f'{_label(item)}: {label} "{value["new"]}" is not printed in its file', 'absent_rate'))
        else:
            others += 1
    return others


def _premium(item, values, counts):
    printed = m.decimal(values.get(PREMIUM))
    if printed is None or not counts:
        return None
    plan = SimpleNamespace(values={key: value for key, value in values.items() if key != PREMIUM})
    computed, _reason, _quoted = m.monthly_premium(plan, SimpleNamespace(rate_basis='composite'), counts)
    if computed is None:
        return None
    moved = m.monthly_change(computed, [printed])
    if moved and abs(moved['delta']) > TOLERANCE:
        return _finding(
            f'{_label(item)}: the printed counts times the rates make ${m.plain(computed):,} a month, but the file '
            f'prints ${m.plain(printed):,}',
            'premium',
        )
    return None


def for_read(items, plans):
    """[finding] for a read's change set; `plans` {id: Plan} are the deal's plans the items may name."""
    out, absent = [], 0
    plan_items = [item for item in items if item.get('op') in PLAN_OPS]
    counts = {}
    for item in items:
        if item.get('op') == 'summary_counts' and item.get('for'):
            target = item['for']
            counts[('item', target['item']) if 'item' in target else ('plan', target.get('plan'))] = item['counts']
    for item in plan_items:
        values = _values(item, plans)
        absent += _absent(item, out)
        if _composite(item['line']):
            if item['op'] == 'create_plan' and not any(values.get(key) for key in (*RATES, PREMIUM)):
                out.append(_finding(f'{_label(item)}: no monthly rates', 'no_rates'))
            out += tier_order(_label(item), values)
            found = counts.get(('item', item['id'])) or counts.get(('plan', item.get('plan')))
            premium = _premium(item, values, found)
            if premium:
                out.append(premium)
    for index, item in enumerate(plan_items):
        for other in plan_items[index + 1 :]:
            same = (item['line'], item.get('role')) == (other['line'], other.get('role'))
            if same and plan_codes.overlap(item.get('codes') or [], other.get('codes') or []):
                out.append(_finding(f'{_label(item)} and {_label(other)} share a plan code', 'shared_code'))
    out += _unpaired(plan_items)
    if absent:
        noun = 'value' if absent == 1 else 'values'
        out.append(_finding(f'{absent} {noun} not found in their file: check them by eye', 'absent'))
    return out


def _renews(renewal):
    target = renewal.get('renews') or {}
    return ('item', target['item']) if 'item' in target else ('plan', target.get('plan'))


def _unpaired(plan_items):
    out = []
    for line in sorted({item['line'] for item in plan_items}):
        on_line = [item for item in plan_items if item['line'] == line]
        renewals = [item for item in on_line if item.get('role') == 'renewal' and item['op'] == 'create_plan']
        if not renewals:
            continue
        renewed = {_renews(renewal) for renewal in renewals}
        for item in on_line:
            if item.get('role') != 'current':
                continue
            if ('item', item['id']) not in renewed and ('plan', item.get('plan')) not in renewed:
                out.append(_finding(f'{_label(item)} has no renewal in this read', 'unpaired'))
    return out


def for_values(plan, values):
    """[finding] for one plan as a chat turn would leave it ({key: new value} over its own)."""
    if not _composite(plan.line):
        return []
    held = {**(plan.values or {}), **{key: value for key, value in values.items() if value not in (None, '')}}
    item = {'carrier': plan.carrier, 'name': plan.name, 'role': plan.role}
    return tier_order(_label(item), held)
