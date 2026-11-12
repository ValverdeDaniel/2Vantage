"""Priced versions (plan.md §5.4, §7.8; F76–F84; OQ7: kept): `plans/priced/` and `plans/{id}/priced/`, each with a
dry run.

A priced version is a copy of a quote with its rates (`copies`' rules: every value with its source, no marks,
approvals or read value; never its original's star, recommendation or sale), then the operations on its rates
(`priced_spec`, `math.pricing`). A changed rate takes a typed source without the file: the carrier's file does not say
the new number. It records `derived_from` and `derived`, rides right behind its original on every screen
(`order.layout`), prices its original's people (`enrollment_for` step 2; F87), takes no option number and never
becomes current (`roles`).
- `price(user, deal, plan_ids, body, dry_run=False)`: one version per plan named, all on one line, all or nothing, in
  one Activity row (`created`; ✕ removes a version through the delete door, which Undo restores). A new version is
  starred when its line has stars and room, so the negotiated price reaches the proposal (F83); never on a line with
  no stars, where one star would hide every other quote (the old bug 17); past the room it is added unstarred, with a
  warning, never refused (refusing would lose the negotiated number).
- `reprice(user, plan_id, body, dry_run=False)` (✎): rebuilt from its original with the new request, so "5% off"
  always means 5% off what the carrier sent and cells typed on the version since are replaced; a version keeps its
  kind; one revertible Activity row; the same request again writes nothing.
The dry run takes the same steps without locks and saves nothing, so its figures are the commit's (F76).
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock, lines
from deals.values import apply as apply_values
from deals.values import source

from .. import presented, priced_spec, signals
from .. import priced_kinds as pk
from ..math.pricing import BelowZero
from ..models import Plan
from ..selectors.priced import preview
from ..selectors.state import line_data, load
from . import locks
from .copies import copied_source, new_plan, replaces_of
from .plans import next_number

# `plans`: the versions (new or re-priced); `drafts`: what each one's draft row shows, in the same order (its preview
# figures, its original and the values it changes there); `row`: the Activity row (None for a dry run or no change).
Priced = namedtuple('Priced', 'plans drafts warning row')

NOT_A_VERSION = 'Only a priced version can be re-priced — this is the carrier’s own quote, or a copy.'
ORIGINAL_GONE = 'The original this version was priced from is gone — edit its cells directly instead.'
KEEPS_KIND = 'A priced version keeps its kind — remove it and add a new one to change what it is.'
ONE_LINE = 'Priced versions apply to one line of business at a time.'


def _lookup(deal):
    """(line, "Carrier Name") of a live plan of the deal, for the quote a bundle requires."""

    def find(plan_id):
        row = Plan.objects.filter(deal=deal, pk=plan_id).values_list('line', 'carrier', 'name').first()
        return None if row is None else (row[0], f'{row[1]} {row[2]}'.strip())

    return find


def _spec(line, body, deal):
    try:
        return priced_spec.clean(line, body, _lookup(deal))
    except priced_spec.SpecError as error:
        raise ValidationError({'detail': str(error)}) from error


def _line(deal, line, locked):
    """The line's live plans {id: plan} and its LineData: locked for a commit, read for a dry run."""
    if locked:
        return locks.line(deal, line)
    rows = load(deal, [line], sources=True)
    return {plan.id: plan for plan in rows}, line_data(line, rows)


def _priced_values(spec, original):
    """The original's values with the version's changes, and the keys whose value changed."""
    try:
        changed = priced_spec.values_for(spec, original.line, original.values)
    except BelowZero as error:
        raise activity.Refused(priced_spec.below_zero(error)) from error
    moved = {key for key, text in changed.items() if text != original.values.get(key)}
    return {**original.values, **changed}, moved


def _sources(user, original, moved):
    """A changed rate is typed, without the file; every other value keeps its original's source."""
    copied, typed = copied_source(original), source('typed', user)
    return lambda key: dict(typed) if key in moved else copied(key)


def _build(user, deal, original, spec, record, name, number):
    """An unsaved version of `original` and its values' before and after."""
    values, moved = _priced_values(spec, original)
    plan = new_plan(
        deal,
        original,
        'alternate',
        name=name,
        derived_from=original,
        derived=dict(record),
        source_document_id=original.source_document_id,
    )
    plan.sort_order = number
    diff = apply_values(plan.values, plan.sources, values, _sources(user, original, moved))
    plan.replaces_ids = replaces_of(original)
    return plan, diff


def _star(data, line, versions, user, now, label):
    """Star the new versions while the line has stars and room (F83); the warning for those left unstarred."""
    if not presented.has_stars(data):
        return ''
    left, unstarred = presented.room(data), 0
    for plan in versions:
        if left <= 0:
            unstarred += 1
            continue
        plan.starred, plan.star_reason = True, label[:100]
        plan.starred_by_id, plan.starred_at = getattr(user, 'id', None), now
        left -= 1
    if not unstarred:
        return ''
    if len(versions) == 1:
        return f'The {lines.label(line)} shortlist is full — the {label} was added unstarred.'
    return f'{unstarred} of {len(versions)} versions were added unstarred — the {lines.label(line)} shortlist is full.'


def _drafts(versions, originals, figures):
    return [
        {
            **shown,
            'original_id': original.id,
            'name': plan.name,
            'label': plan.derived.get('label', ''),
            'derived': {key: value for key, value in plan.derived.items() if key not in ('by', 'at')},
            'starred': plan.starred,
            'changes': {key: value for key, value in plan.values.items() if original.values.get(key) != value},
        }
        for plan, original, shown in zip(versions, originals, figures, strict=True)
    ]


def _summary(originals, label):
    if len(originals) == 1:
        return f'Priced {originals[0].carrier} {originals[0].name}: {label}'
    carriers = ' / '.join(sorted({plan.carrier for plan in originals}))
    return f'Priced {len(originals)} plans ({carriers}): {label}'


def _price(user, deal, ids, body, locked):
    found = dict(Plan.objects.filter(deal=deal, id__in=ids).values_list('id', 'line'))
    if len(found) != len(ids):
        raise ValidationError({'plan_ids': ['A plan is not on this deal.']})
    if len(set(found.values())) > 1:
        raise activity.Refused(ONE_LINE)
    line = found[ids[0]]
    rows, data = _line(deal, line, locked)
    spec = _spec(line, body, deal)
    originals = [rows[plan_id] for plan_id in ids]
    if spec.kind == pk.HOLIDAY and 'annual' in spec.credit and len(originals) > 1:
        raise activity.Refused(pk.WORDS['one_plan_credit'])
    for original in originals:
        why = priced_spec.refusal(original, spec.kind)
        if why:
            raise activity.Refused(why)
    now = clock.now()
    record = priced_spec.record(spec, getattr(user, 'id', None), now.isoformat())
    first, multi = next_number(deal, line), len(originals) > 1
    built = [
        _build(user, deal, original, spec, record, priced_spec.name_for(original.name, spec, multi), first + at)
        for at, original in enumerate(originals)
    ]
    versions = [plan for plan, _diff in built]
    warning = _star(data, line, versions, user, now, spec.label)
    drafts = _drafts(versions, originals, preview(line, list(rows.values()), versions))
    if not locked:
        return Priced(versions, drafts, warning, None)
    changes = []
    for plan, diff in built:
        plan.save()
        plan.replaces.set(plan.replaces_ids)
        star = {'plan.starred': [False, True], 'plan.star_reason': ['', plan.star_reason]} if plan.starred else {}
        changes.append(activity.change(f'plan:{plan.id}', {**diff, **star}))
    row = activity.record(deal, user, 'quotes', 'created', _summary(originals, spec.label), changes=changes)
    signals.changed(deal.id, [line])
    return Priced(versions, drafts, warning, row)


def price(user, deal, plan_ids, body, dry_run=False):
    """`plans/priced/` {plan_ids, kind, …}: a version of each plan named. Returns `Priced`."""
    ids = list(dict.fromkeys(plan_ids))
    if not ids:
        raise ValidationError({'plan_ids': ['Pick at least one plan to price.']})
    if dry_run:
        return _price(user, deal, ids, body, locked=False)
    with transaction.atomic():
        return _price(user, locks.deal(deal.id), ids, body, locked=True)


def _rebuild(user, version, original, spec, record):
    """Re-price `version` in memory from its original; its values' before and after."""
    values, moved = _priced_values(spec, original)
    updates = {key: values.get(key, '') for key in {*version.values, *values}}
    for key in moved:
        if version.values.get(key) != updates[key]:
            version.sources.pop(key, None)  # a typed rate over a copied one keeps no file
    diff = apply_values(version.values, version.sources, updates, _sources(user, original, moved))
    before = version.derived or {}
    name = version.name
    if spec.name:
        name = spec.name[:200]
    elif name == f'{original.name} — {before.get("label", "")}'[:200]:  # the default name follows the label
        name = priced_spec.name_for(original.name, spec)
    if name != version.name:
        diff['plan.name'] = [version.name, name]
        version.name = name
    if not priced_spec.same(before, record):
        diff['plan.derived'] = [before, record]
        version.derived = record
    return diff


def _reprice(user, deal, plan_id, line, body, locked):
    rows, _data = _line(deal, line, locked)
    version = rows[plan_id]
    kind = (version.derived or {}).get('kind')
    if not version.derived_from_id or kind not in pk.KINDS:
        raise activity.Refused(NOT_A_VERSION)
    original = rows.get(version.derived_from_id)
    if original is None:
        raise activity.Refused(ORIGINAL_GONE)
    spec = _spec(line, body, deal)
    if spec.kind != kind:
        raise activity.Refused(KEEPS_KIND)
    why = priced_spec.refusal(version, kind) or (None if original.sold else priced_spec.refusal(original, kind))
    if why:
        raise activity.Refused(why)
    record = priced_spec.record(spec, getattr(user, 'id', None), clock.now().isoformat())
    diff = _rebuild(user, version, original, spec, record)
    drafts = _drafts([version], [original], preview(line, list(rows.values()), [version]))
    if not locked:
        return Priced([version], drafts, '', None)
    if not diff:  # the same request again: nothing to write
        return Priced([], drafts, '', None)
    version.save()
    summary = f'Re-priced {version.carrier} {version.name}: {spec.label}'
    changes = [activity.change(f'plan:{version.id}', diff)]
    row = activity.record(deal, user, 'quotes', 'updated', summary, changes=changes)
    signals.changed(deal.id, [line])
    return Priced([version], drafts, '', row)


def reprice(user, plan_id, body, dry_run=False):
    """`plans/{id}/priced/` {kind, …}: ✎ re-price a version from its original. Returns `Priced`."""
    if dry_run:
        plan = Plan.objects.select_related('deal').get(pk=plan_id)
        return _reprice(user, plan.deal, plan_id, plan.line, body, locked=False)
    with transaction.atomic():
        deal = locks.plan_deal(plan_id)
        line = Plan.objects.values_list('line', flat=True).get(pk=plan_id)
        return _reprice(user, deal, plan_id, line, body, locked=True)
