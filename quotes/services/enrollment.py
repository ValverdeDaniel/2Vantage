"""Typed enrollment (plan.md §5.5; F85, F88, F90, F91, F92, O.6 #10): one door for a line's whole typed set — the
plans' own counts, the figure typed for the whole line, the line's one switch, the census plan texts a person matched
to its current plans, and "Keep my typed counts". The Advisor's counts card and the builder's EnrollmentStrip (J48,
slice 25) both call `set_enrollment`.

- `plans` is the line's whole per-plan set, `[{id, enrollment}]`: a plan of the line it leaves out loses its counts.
- `whole_line` is the line figure (`{}` or None clears it); `on` the switch; `census_names` `{plan id: [texts]}` for
  current plans (a text given to one plan leaves the others); `keep` stamps typed counts saved before the latest census
  import as typed now, so they price again (F91).
- Any change to typed figures stamps `typed_at` now and `census_seen` with the deal's applied census imports: counts
  typed after the import win. The count decides, not the clock (`shapes.People.stale`); both writers lock the Deal
  first, so a save and an import are ordered by the lock.
Each argument left out leaves its part as it is. Locks the Deal, then the line's plans by id, then its LineEnrollment.
An unchanged save writes nothing (§3.7): not the counts, not `typed_at`, not Activity. One Activity row, area
`enrollment`, with before and after per key; `revert.revert_enrollment` puts them back.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock, lines

from .. import math as m
from .. import signals
from ..math import by_plan
from ..models import LineEnrollment
from ..selectors import people as known
from ..shapes import People
from . import locks

AREA = 'enrollment'
UNSET = object()
TEXT_LIMIT = 200
Saved = namedtuple('Saved', 'plans line activity')


def line_target(line):
    return f'{AREA}:{line}'


def clean_figures(raw, keys, name):
    """{key: number} for the basis's keys, whole numbers of people (a volume may carry cents); {} when all are 0."""
    if raw in (None, ''):
        return {}
    if not isinstance(raw, dict):
        raise ValidationError({'enrollment': ['Enrollment must be an object.']})
    unknown = set(raw) - set(keys)
    if unknown:
        raise ValidationError({'enrollment': [f'{name} takes {", ".join(keys)}, not {", ".join(sorted(unknown))}']})
    cleaned = {}
    for key in keys:
        value = raw.get(key, 0)
        try:
            number = float(str(value).replace(',', '').strip() or 0)
        except ValueError as exc:
            raise ValidationError({'enrollment': [f'{key} takes a number, not "{value}"']}) from exc
        if number < 0 or (key != 'volume' and number != int(number)):
            raise ValidationError({'enrollment': [f'{key} takes a whole number of 0 or more']})
        cleaned[key] = int(number) if number == int(number) else number
    return cleaned if any(cleaned.values()) else {}


def _plan_items(items, rows, keys, line_label):
    if not isinstance(items, list):
        raise ValidationError({'plans': ['Send the line’s plans as a list of {id, enrollment}.']})
    wanted = {}
    for item in items:
        try:
            plan_id = int(item.get('id'))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValidationError({'plans': ['Each row names a plan id.']}) from exc
        if plan_id not in rows:
            raise ValidationError({'plans': [f'Plan {plan_id} is not a plan on {line_label}.']})
        wanted[plan_id] = clean_figures(item.get('enrollment'), keys, rows[plan_id].name)
    return wanted


def _names(raw, rows, line_label):
    if not isinstance(raw, dict):
        raise ValidationError({'census_names': ['Send {plan id: [census plan texts]}.']})
    out = {}
    for key, texts in raw.items():
        try:
            plan_id = int(key)
        except (TypeError, ValueError) as exc:
            raise ValidationError({'census_names': ['Each key is a plan id.']}) from exc
        plan = rows.get(plan_id)
        if plan is None or plan.role != 'current':
            raise ValidationError({'census_names': [f'Plan {plan_id} is not a current plan on {line_label}.']})
        if not isinstance(texts, list) or not all(isinstance(text, str) for text in texts):
            raise ValidationError({'census_names': ['Each plan takes a list of census plan texts.']})
        cleaned = list(dict.fromkeys(text.strip() for text in texts if text.strip()))
        if any(len(text) > TEXT_LIMIT for text in cleaned):
            raise ValidationError({'census_names': [f'A census plan text takes at most {TEXT_LIMIT} characters.']})
        out[plan_id] = cleaned
    return out


def _diff(before, after, prefix):
    return {
        f'{prefix}{key}': [before.get(key), after.get(key)]
        for key in dict.fromkeys([*before, *after])
        if before.get(key) != after.get(key)
    }


def _line_row(deal, line):
    row = LineEnrollment.objects.select_for_update().filter(deal=deal, line=line).first()
    return row or LineEnrollment(deal=deal, line=line)


def _with_names(rows, names):
    """{plan id: census_names after}: each named plan takes its texts, and a text it takes leaves every other plan."""
    taken = {by_plan.norm(text): plan_id for plan_id, texts in names.items() for text in texts}
    out = {}
    for plan in rows.values():
        if plan.role != 'current':
            continue
        if plan.id in names:
            out[plan.id] = names[plan.id]
        else:
            out[plan.id] = [
                text for text in plan.census_names or [] if taken.get(by_plan.norm(text), plan.id) == plan.id
            ]
    return out


def _summary(counts, kept, switched, matched, label):
    if counts:
        return f'Edited enrollment on {label}'
    if kept:
        return f'Kept the typed counts on {label} over the census'
    if switched is not None:
        return f'Switched typed counts {"on" if switched else "off"} on {label}'
    return f'Matched census plan names on {label}' if matched else ''


@transaction.atomic
def set_enrollment(user, deal, line, *, plans=UNSET, whole_line=UNSET, on=UNSET, census_names=UNSET, keep=False):
    if line not in lines.BY_KEY:
        raise ValidationError({'line': ['Give a line of coverage.']})
    label = lines.label(line)
    keys = m.enrollment_keys(lines.BY_KEY[line]['rate_basis'])
    deal = locks.deal(deal.id)
    rows, _data = locks.line(deal, line)
    wanted = _plan_items(plans, rows, keys, label) if plans is not UNSET else None
    figure = clean_figures(whole_line, keys, label) if whole_line is not UNSET else None
    names = _with_names(rows, _names(census_names, rows, label)) if census_names is not UNSET else {}
    if on is not UNSET and not isinstance(on, bool):
        raise ValidationError({'on': ['The switch is true or false.']})
    row = _line_row(deal, line)
    changes, changed = [], []
    for plan in sorted(rows.values(), key=lambda p: p.id):
        diff = {}
        if wanted is not None:
            diff.update(_diff(plan.enrollment or {}, wanted.get(plan.id, {}), 'enrollment.'))
        if plan.id in names and names[plan.id] != list(plan.census_names or []):
            diff['census_names'] = [list(plan.census_names or []), names[plan.id]]
        if diff:
            if wanted is not None:
                plan.enrollment = wanted.get(plan.id, {})
            plan.census_names = names.get(plan.id, plan.census_names)
            plan.save(update_fields=['enrollment', 'census_names', 'updated_at'])
            changes.append(activity.change(f'plan:{plan.id}', diff))
            changed.append(plan)
    counts = any(key.startswith('enrollment.') for entry in changes for key in entry['k'])
    line_diff = _diff(row.enrollment or {}, figure, 'figure.') if figure is not None else {}
    counts = counts or bool(line_diff)
    switched = on if on is not UNSET and on != row.on else None
    if switched is not None:
        line_diff['on'] = [row.on, on]
    typed = any(p.enrollment for p in rows.values()) or bool(figure if figure is not None else row.enrollment)
    imports = known.applied_imports(deal.id)
    kept = keep and typed and People(imports=imports, census_seen=row.census_seen).stale
    if counts or kept:
        now = clock.now()
        line_diff['typed_at'] = [row.typed_at.isoformat() if row.typed_at else None, now.isoformat()]
        row.typed_at = now
        if row.census_seen != imports:
            line_diff['census_seen'] = [row.census_seen, imports]
            row.census_seen = imports
    if line_diff:
        row.enrollment = figure if figure is not None else row.enrollment
        row.on = on if switched is not None else row.on
        row.save()
        changes.append(activity.change(line_target(line), line_diff))
    if not changes:
        return Saved([], None, None)
    record = activity.record(
        deal, user, AREA, 'updated', _summary(counts, kept, switched, bool(names), label), changes=changes
    )
    signals.changed(deal.id, [line])
    return Saved(changed, row if line_diff else None, record)
