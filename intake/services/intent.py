"""The coverage intent: the card's two controls, its ×, the Lines-to-quote chips, Confirm and Reopen (plan.md §5.2,
§7.6; B16–B20, B32; OQ15).

`set_intent` is the only writer of `Deal.requested_lines`: it calls `deals.services.set_lines` in the same transaction
as the coverage rows it writes, so a gesture is never half applied (the old app's `CoverageIntentView`, 891f1b3). One
call names one line (`line`) or many (`lines`, the select-all headers and the New client dialog), validated in full
before anything is written, and one control:
- `has_today` (bool) and/or `this_year` (market, keep or off): the card's controls. A control left out keeps what
  each line says today. Answering a line that has no row creates it (the moment a line stops being unanswered).
- `shop` (bool): the Lines-to-quote chips and the deal header's Lines picker. It adds the line to or takes it off the
  lines to quote and never creates a row; on an answered row, shopping again also puts it back on the proposal, so
  the row keeps one of the card's three choices.
- `remove` (one line only): the card's ×. Every row of the line goes, and so does the line from the lines to quote.
One Activity row (area `intake`) holds every change, the deal's `requested_lines` included; Revert puts it all back.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from deals import lines as line_vocab
from deals.services import set_lines

from .. import coverage
from ..models import CurrentCoverage, Intake
from ..signals import announce
from . import rows

Changed = namedtuple('Changed', 'lines rows activity')  # lines: [before, after] or None; rows: {target: diff}

NOTHING = 'Say what to change: has_today, this_year, shop or remove.'


def _targets(line, many):
    if many is not None:
        if not isinstance(many, list) or not all(isinstance(key, str) for key in many):
            raise ValidationError({'lines': ['Send a list of line keys.']})
        keys = list(dict.fromkeys(key.strip() for key in many))
        if not keys:
            raise ValidationError({'lines': ['Name at least one line of coverage.']})
    else:
        keys = [str(line or '').strip()]
    unknown = [key for key in keys if key not in line_vocab.BY_KEY]
    if unknown:
        field = 'line' if many is None else 'lines'
        raise ValidationError({field: [f'Unknown line: {", ".join(unknown) or "(blank)"}']})
    return keys


def _controls(has_today, this_year, shop, remove, many):
    errors = {}
    for name, value in (('has_today', has_today), ('shop', shop)):
        if value is not None and not isinstance(value, bool):
            errors[name] = ['Send true or false.']
    if this_year is not None and this_year not in coverage.THIS_YEAR:
        errors['this_year'] = [f'Choose one of: {", ".join(coverage.THIS_YEAR)}.']
    if remove and many is not None:
        errors['lines'] = ['Remove takes one line at a time.']
    if shop is not None and (has_today is not None or this_year is not None or remove):
        errors['shop'] = ['Send shop on its own.']
    if not errors and has_today is None and this_year is None and shop is None and not remove:
        errors['non_field_errors'] = [NOTHING]
    if errors:
        raise ValidationError(errors)


def _words(keys):
    labels = [line_vocab.label(key) for key in keys]
    return labels[0] if len(labels) == 1 else f'{len(labels)} lines'


def _summary(keys, has_today, this_year, shop, remove):
    if remove:
        return f'Took {_words(keys)} out of the coverage intent'
    if shop is not None:
        return f'Lines to quote: {"added" if shop else "removed"} {_words(keys)}'
    parts = []
    if has_today is not None:
        parts.append('in force' if has_today else 'not in force')
    if this_year is not None:
        parts.append(coverage.THIS_YEAR_LABELS[True][this_year])
    return f'Coverage intent: {_words(keys)} {", ".join(parts)}'


@transaction.atomic
def set_intent(user, deal_id, *, line=None, lines=None, has_today=None, this_year=None, shop=None, remove=False):
    """Apply one gesture of the card or the chips. Returns Changed(lines, rows, activity); nothing changed writes
    nothing (no row, no Activity)."""
    keys = _targets(line, lines)
    _controls(has_today, this_year, shop, remove, lines)
    deal = rows.lock_deal(deal_id)
    current = rows.lock_coverage(deal_id)
    first = coverage.first_rows(current)
    wanted = set(deal.requested_lines or [])
    entries, next_order = {}, None

    def decide(key):
        row = first.get(key)
        shopping = key in wanted
        if shop is not None:
            return (row.in_force, shop, True if shop else row.on_proposal) if row else (None, shop, None)
        in_force = has_today if has_today is not None else (row.in_force if row else False)
        year = this_year or coverage.this_year_of(shopping, row.on_proposal if row else True)
        return coverage.controls_to_intent(in_force, year)

    if remove:
        key = keys[0]
        for row in [row for row in current if row.line == key]:
            entries[rows.target(row.id)] = rows.removed(rows.state(row))
            row.delete()
        wanted.discard(key)
    else:
        for key in keys:
            in_force, shopping, on_proposal = decide(key)
            (wanted.add if shopping else wanted.discard)(key)
            row = first.get(key)
            if in_force is None:  # `shop` on an unanswered line: only the lines to quote change
                continue
            if row is None:
                if next_order is None:
                    next_order = rows.next_sort_order(deal_id)
                row = CurrentCoverage.objects.create(
                    deal=deal, line=key, in_force=in_force, on_proposal=on_proposal, sort_order=next_order
                )
                next_order += 1
                entries[rows.target(row.id)] = rows.created(row)
            elif (row.in_force, row.on_proposal) != (in_force, on_proposal):
                before = rows.state(row)
                row.in_force, row.on_proposal = in_force, on_proposal
                row.save(update_fields=['in_force', 'on_proposal'])
                entries[rows.target(row.id)] = rows.changed(before, row)
    lines_diff = set_lines(deal_id, [key for key in line_vocab.LINE_KEYS if key in wanted])
    if not entries and not lines_diff:
        return Changed(None, {}, None)
    changes = [activity.change(f'deal:{deal_id}', lines_diff)] if lines_diff else []
    changes += [activity.change(t, diff) for t, diff in entries.items()]
    summary = _summary(keys, has_today, this_year, shop, remove)
    row = activity.record(deal, user, rows.AREA, 'intent', summary, changes=changes)
    announce(deal_id)
    return Changed(lines_diff.get('requested_lines'), entries, row)


def _stamp(user, decisions):
    by = user if getattr(user, 'is_authenticated', False) else None
    return {
        'decisions': decisions,
        'by': getattr(by, 'id', None),
        'by_name': (by.get_full_name() or by.username) if by else '',
        'at': clock.now().isoformat(),
    }


def _write_confirmation(user, deal_id, value, action, summary):
    deal = rows.lock_deal(deal_id)
    if not value and not Intake.objects.filter(deal_id=deal_id).exists():
        return None  # nothing confirmed, and a reopen never creates the row
    intake = rows.lock_intake(deal_id)
    before = intake.intent_confirmed or {}
    if before == value:
        return None
    intake.intent_confirmed = value
    intake.save(update_fields=['intent_confirmed', 'updated_at'])
    entry = activity.change(rows.intake_target(deal_id), {'intent_confirmed': [before, value]})
    return activity.record(deal, user, rows.AREA, action, summary, changes=[entry])


@transaction.atomic
def confirm_intent(user, deal_id):
    """Confirm coverage and intent (B20): store today's decisions. Confirming unchanged decisions again writes
    nothing. Returns the Activity row, or None."""
    from ..selectors import intent_rows_for

    rows.lock_deal(deal_id)
    current = coverage.decisions(intent_rows_for(deal_id))
    stored = Intake.objects.filter(deal_id=deal_id).values_list('intent_confirmed', flat=True).first() or {}
    if stored.get('decisions') == current:
        return None
    return _write_confirmation(user, deal_id, _stamp(user, current), 'confirmed', 'Confirmed coverage & intent')


@transaction.atomic
def reopen_intent(user, deal_id):
    """Reopen: drop the confirmation. Nothing to drop writes nothing. Returns the Activity row, or None."""
    return _write_confirmation(user, deal_id, {}, 'reopened', 'Reopened coverage & intent')
