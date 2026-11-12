"""Scoring a read against its corpus key (plan.md §12.8; Q.6's metrics). Pure: counts only, never a value.

`score(key, merged)` compares the plans a read found (`merge.merge`'s answer) with the plans the file prints:
plans found and invented, sides and renewal links, the printed column order, rate cells to the cent, wrong rates with
no doubt, design values after house formats, and values written where the key has none. `ai/eval` adds the counts up
per set and checks Q.6's thresholds.
"""

from .. import values as house
from .merge import norm

RATE_PREFIXES = ('rate_', 'unit_rate', 'group_premium', 'contrib_', 'lf_', 'sl_')


def _same(found, plan):
    return found['line'] == plan['line'] and found['side'] == plan['side'] and norm(found['name']) == norm(plan['name'])


def _clean(key, value):
    from .rules import clean

    cleaned, _why = clean(key, value)
    return cleaned


def score(key, merged):
    found = list(merged.get('plans') or [])
    counts = dict.fromkeys(
        (
            'plans_key',
            'plans_found',
            'plans_matched',
            'roles',
            'roles_right',
            'order_cases',
            'order_exact',
            'rates',
            'rates_exact',
            'rates_wrong_unflagged',
            'design',
            'design_right',
            'key_blank',
            'written_on_blank',
        ),
        0,
    )
    counts['plans_key'], counts['plans_found'] = len(key['plans']), len(found)
    pairs = []
    for plan in key['plans']:
        hit = next((f for f in found if _same(f, plan)), None)
        if hit is not None:
            pairs.append((plan, hit))
    counts['plans_matched'] = len(pairs)
    by_key = {f['key']: f for f in found}
    for plan, hit in pairs:
        counts['roles'] += 1
        renews = by_key.get(hit.get('renews'))
        if (renews['name'] if renews else None) == plan['renews'] or (
            plan['renews'] and renews and norm(renews['name']) == norm(plan['renews'])
        ):
            counts['roles_right'] += 1
        for field_key, expected in plan['values'].items():
            got = hit['values'].get(field_key) or {}
            value = _clean(field_key, got.get('value', '')) if got else None
            if field_key.startswith(RATE_PREFIXES):
                counts['rates'] += 1
                if value is not None and house.as_float(value) == house.as_float(expected):
                    counts['rates_exact'] += 1
                elif not got.get('unsure'):
                    counts['rates_wrong_unflagged'] += 1
            else:
                counts['design'] += 1
                if value is not None and norm(value) == norm(_clean(field_key, expected) or expected):
                    counts['design_right'] += 1
        for field_key in hit['values']:
            if field_key not in plan['values']:
                counts['written_on_blank'] += 1
        counts['key_blank'] += max(len(hit['values']), len(plan['values'])) - len(plan['values'])
    order_key = [(p['side'], norm(p['name'])) for p in key['plans']]
    order_found = [(f['side'], norm(f['name'])) for f in found if any(_same(f, p) for p in key['plans'])]
    counts['order_cases'] = 1
    counts['order_exact'] = int(order_key == order_found)
    return counts
