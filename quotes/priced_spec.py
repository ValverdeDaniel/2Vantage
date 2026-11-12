"""What a priced version is made of (plan.md §5.4, §6.7; F77, F78, F80, F82; the old concessions._clean_spec): a
request cleaned into a `Spec`, its `derived` record, its label and name, the version's changed values, and the
refusals on a plan. Pure.

One cleaner behind the create, its dry run and ✎ re-price, so the three never disagree about what a valid version is
(the old app's rule). Malformed input raises `SpecError` (a 400 with the sentence); `refusal(plan, kind)` words why a
plan cannot take a version (a 409). The request:
- concession: `all` {op, value} on every rate (a percentage also reaches the quoted group premium, a dollar amount or
  a set-to does not), and `each` {rate key: {op, value} | "keep"} one rate at a time ("keep" leaves a rate out);
- bundle: `parts` [{line, op, value, plan_id?, carrier?}], the quote (or carrier) that has to sell, and `conditional`;
- holiday: `credit` {annual} (dollars a year) or {months} (free months, 1 to 12).
"""

from dataclasses import dataclass, field

from deals import lines

from . import fields
from . import priced_kinds as pk
from .math import pricing
from .math.rounding import decimal, plain, round_decimal

OVER = 'A priced version'


class SpecError(ValueError):
    """Input a priced version cannot be made of; the message is the sentence shown."""


@dataclass
class Spec:
    kind: str
    note: str = ''
    name: str = ''
    label: str = ''
    all: dict | None = None
    each: dict = field(default_factory=dict)
    ops: list = field(default_factory=list)
    parts: list = field(default_factory=list)
    conditional: bool = True
    credit: dict | None = None

    @property
    def requires(self):
        return [part['plan_id'] for part in self.parts if part.get('plan_id')]


def _label_of(key):
    return fields.BY_KEY.get(key, {}).get('label', key)


def _words(number):
    return f'{plain(number):g}'


def _money(number):
    return f'${plain(number):,.2f}'.replace('.00', '')


def _change(raw, label, allowed):
    """{op, value} from the request, the value to 4 places."""
    if not isinstance(raw, dict):
        raise SpecError(f'{label}: give a change and an amount.')
    op = str(raw.get('op') or '').strip()
    if op not in allowed:
        raise SpecError(f'{label}: unknown change "{op}".')
    value = decimal(raw.get('value'))
    if value is None:
        raise SpecError(f'{label} needs a number for its change.')
    if op in pk.PCT_OPS and not 0 < value < 100:
        raise SpecError(f'{label}: the percentage must be between 0 and 100.')
    if op not in pk.PCT_OPS and value < 0:
        raise SpecError(f'{label} needs a non-negative dollar amount.')
    return {'op': op, 'value': plain(round_decimal(value, 4))}


def _concession_label(ops, rate_keys):
    """One change on every rate reads as what it is ("5% concession", "$10 off"); anything mixed is "concession"."""
    shapes = {(op['op'], op['value']) for op in ops}
    if len(shapes) != 1 or not set(rate_keys) <= {op['key'] for op in ops}:
        return 'concession'
    op, value = next(iter(shapes))
    words = {
        'pct_off': f'{_words(value)}% concession',
        'pct_up': f'{_words(value)}% increase',
        'flat_off': f'{_money(value)} off',
        'flat_up': f'{_money(value)} increase',
    }
    return words.get(op, 'concession')


def _concession(spec, line, body):
    basis = lines.BY_KEY[line]['rate_basis']
    keys, rates = pk.premium_keys(basis), pk.rate_keys(basis)
    if body.get('all') not in (None, '', {}):
        spec.all = _change(body['all'], 'All rates', pk.OP_KEYS)
    each = body.get('each') or {}
    if not isinstance(each, dict):
        raise SpecError('Each rate takes a change per rate.')
    for key, item in each.items():
        if key not in keys:
            raise SpecError(
                f'“{_label_of(key)}” isn’t a rate on the {lines.label(line)} line — a changed plan design is a new '
                'quote, not a priced version.'
            )
        spec.each[key] = pk.KEEP if item == pk.KEEP else _change(item, _label_of(key), pk.OP_KEYS)
    expanded = {}
    if spec.all:
        expanded = {key: spec.all for key in (keys if spec.all['op'] in pk.PCT_OPS else rates)}
    for key, item in spec.each.items():
        if item == pk.KEEP:
            expanded.pop(key, None)
        else:
            expanded[key] = item
    spec.ops = [{'key': key, **expanded[key]} for key in keys if key in expanded]
    if not spec.ops:
        raise SpecError('Set a change for all rates, or for at least one rate.')
    spec.label = _concession_label(spec.ops, rates)


def _required(item, line, lookup):
    """The quote that has to sell for the discount, as {plan_id, plan_label}; or the carrier, with no quote yet."""
    label = lines.label(line)
    raw = item.get('plan_id')
    if raw not in (None, '', 0):
        if isinstance(raw, bool):
            raise SpecError(f'{label}: that is not a plan id.')
        try:
            plan_id = int(raw)
        except (TypeError, ValueError) as exc:
            raise SpecError(f'{label}: that is not a plan id.') from exc
        found = lookup(plan_id)
        if found is None:
            raise SpecError(f'{label}: the plan this bundle requires is not on this deal.')
        on, words = found
        if on != line:
            raise SpecError(f'{label}: {words} is a {lines.label(on)} plan.')
        return {'plan_id': plan_id, 'plan_label': words}
    carrier = str(item.get('carrier') or '').strip()[:200]
    return {'carrier': carrier} if carrier else {}


def _bundle_label(parts, pct, flat):
    bits = []
    if pct:
        bits.append(f'{_words(abs(pct))}%' + ('' if pct > 0 else ' up'))
    if flat:
        bits.append(_money(abs(flat)) + ('' if flat > 0 else ' up'))
    names = ' + '.join(lines.label(part['line']) for part in parts)
    return f'{" + ".join(bits)} bundled ({names})'.strip()


def _bundle(spec, body, lookup):
    raw = body.get('parts')
    if not isinstance(raw, list):
        raise SpecError('A bundling discount takes its lines as a list.')
    for item in raw:
        if not isinstance(item, dict) or item.get('line') not in lines.BY_KEY:
            raise SpecError('Each bundled line needs a known line of coverage.')
        line = item['line']
        value = decimal(item.get('value'))
        if value is None or value <= 0:
            continue  # an untouched line is simply not bundled
        if any(part['line'] == line for part in spec.parts):
            raise SpecError(f'{lines.label(line)} is in the bundle twice.')
        op = str(item.get('op') or 'pct_off').strip()
        if op not in pk.BUNDLE_OPS:
            raise SpecError(f'{lines.label(line)}: unknown bundling change "{op}".')
        if op in pk.PCT_OPS and not 0 < value < 50:
            raise SpecError(f'{lines.label(line)}: a bundling percentage must be between 0 and 50.')
        part = {'line': line, 'op': op, 'value': plain(round_decimal(value, 4))}
        spec.parts.append({**part, **_required(item, line, lookup)})
    if not spec.parts:
        raise SpecError(
            'A bundling discount needs at least one line of business with a percentage or a dollar amount '
            '(e.g. dental 2%, vision 0.5%).'
        )
    pct, flat = pricing.bundle_totals(spec.parts)
    if not -100 < pct < 100:
        raise SpecError(f'The bundled percentages sum to {_words(pct)}% — the total discount must stay under 100%.')
    spec.conditional = body.get('conditional', True) not in (False, 'false', 0)
    spec.label = _bundle_label(spec.parts, pct, flat)


def _holiday(spec, body):
    raw = body.get('credit') if isinstance(body.get('credit'), dict) else {}
    annual, months = decimal(raw.get('annual')), decimal(raw.get('months'))
    if annual is None and months is None:
        raise SpecError('A premium holiday needs a dollar credit or a number of free months.')
    if annual is not None:
        if annual <= 0:
            raise SpecError('The premium-holiday credit must be a positive dollar amount.')
        spec.credit = {'annual': plain(round_decimal(annual, 2))}
    else:
        if not 0 < months <= 12:
            raise SpecError('Free months must be between 1 and 12.')
        spec.credit = {'months': plain(round_decimal(months, 4))}
    spec.label = 'premium holiday'


def clean(line, body, lookup):
    """The request as a Spec. `lookup(plan_id)` → (line, "Carrier Name") for a live plan of the deal, else None."""
    if not isinstance(body, dict):
        raise SpecError(f'{OVER} is sent as an object.')
    kind = body.get('kind')
    if kind not in pk.KINDS:
        raise SpecError('Pick a concession, a bundling discount or a premium holiday.')
    spec = Spec(kind=kind, note=str(body.get('note') or '').strip()[:1000], name=str(body.get('name') or '').strip())
    if kind == pk.CONCESSION:
        _concession(spec, line, body)
    elif kind == pk.BUNDLE:
        _bundle(spec, body, lookup)
    else:
        _holiday(spec, body)
    return spec


def record(spec, by, at):
    """The version's `derived` record (§6.7): plain JSON, so Activity keeps it and Revert compares it as stored."""
    out = {'kind': spec.kind, 'label': spec.label, 'note': spec.note}
    if spec.kind == pk.CONCESSION:
        out.update(ops=spec.ops, all=spec.all, each=spec.each)
    elif spec.kind == pk.BUNDLE:
        pct, flat = pricing.bundle_totals(spec.parts)
        out.update(parts=spec.parts, pct=plain(pct), flat=plain(flat), requires=spec.requires)
        out['conditional'] = spec.conditional
    else:
        out['credit'] = spec.credit
    return {**out, 'by': by, 'at': at}


def same(a, b):
    """Whether two records make the same version (who and when aside)."""

    def kept(record):
        return {key: value for key, value in (record or {}).items() if key not in ('by', 'at')}

    return kept(a) == kept(b)


def values_for(spec, line, values):
    """{key: text} the version changes; pricing.BelowZero when a rate would go below zero."""
    basis = lines.BY_KEY[line]['rate_basis']
    if spec.kind == pk.CONCESSION:
        return pricing.concession(values, spec.ops)
    if spec.kind == pk.BUNDLE:
        pct, flat = pricing.bundle_totals(spec.parts)
        return pricing.bundle(values, pk.rate_keys(basis), pct, flat)
    return {}


def below_zero(error):
    return f'{_label_of(error.key)}: the change lands below zero ({error.amount}).'


def name_for(original_name, spec, multi=False):
    """A typed name on one version stands as typed; across several it is each plan's suffix; else the label is."""
    if spec.name and not multi:
        return spec.name[:200]
    return f'{original_name} — {spec.name or spec.label}'[:200]


def refusal(plan, kind):
    """Why `plan` cannot take a version of `kind`, or None (the old `_guard_plan`; a lost deal no longer refuses)."""
    words = f'{plan.carrier} — {plan.name}'
    if plan.sold:
        return f'{words} is already sold: final rates are confirmed with the carrier at close-out, not re-priced here.'
    if plan.role == 'current' and kind != pk.HOLIDAY:
        return (
            'The current plan is the in-force baseline — apply the concession to the carrier’s quote or renewal '
            'column instead.'
        )
    if kind == pk.BUNDLE and plan.bundling == 'included':
        return (
            f'{words}: the quoted rates already include the bundling discount — a bundled version would discount them '
            'twice.'
        )
    return None
