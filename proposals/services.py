"""Writes to the proposal configuration and the builder's marks (plan.md §6.11, §7.12; J18–J20, J.6.4).

- `set_config(user, deal, changes)`: `{path: value}` merged by path under the row's lock (`config.merge`), so two
  people writing different paths both keep theirs; an unchanged path writes nothing; the marks of the cards owning the
  changed paths come off in the same write (J19). One Activity row a call (area `proposal`, coalesced like every edit
  of the same person), with before and after per path.
- `set_mark(user, deal, card, line, done)`: a card marked completed or not (J18); its own Activity row, never merged.
- `clear_marks(deal_id, lines, cards)`: quotes' `plans_changed` receiver — a star, slot, order or Claude write takes
  the line's Plans card mark off (J19). One JSONB key removal, no read; no Activity of its own (the quotes write is).
Lock order (rule 3): the Deal first (it serializes the row's creation), then the config row.
"""

from collections import namedtuple

from django.db import transaction
from django.db.models.expressions import RawSQL
from rest_framework.exceptions import ValidationError

from deals import activity, clock, lines
from deals.models import Deal

from . import catalog, config, marks
from .models import ProposalConfig

AREA = 'proposal'
MARKED = 'marked'  # a mark's Activity action: never merged (deals.activity.NEVER_MERGE)
Written = namedtuple('Written', 'changed cleared activity')  # {path: value}, [mark paths], Activity row or None


def target(deal_id):
    return f'proposal:{deal_id}'


def _locked(deal_id):
    """(the Deal, the config row or None), locked in that order."""
    deal = Deal.objects.select_for_update().get(pk=deal_id)
    return deal, ProposalConfig.objects.select_for_update().filter(deal_id=deal_id).first()


def _mark_key(mark_path):
    return mark_path.removeprefix('marks.')


def _take_off(row, mark_paths):
    """{mark path: [stamp, None]} for the marks removed from `row.marks`, in memory."""
    out = {}
    for path in mark_paths:
        key = _mark_key(path)
        before = config.get(row.marks, key) or None
        if before:
            config.drop(row.marks, key)
            out[path] = [before, None]
    return out


@transaction.atomic
def set_config(user, deal, changes):
    """Returns Written({path: new value}, [mark paths cleared], Activity row or None)."""
    deal, row = _locked(deal.pk)
    try:
        merged, diff = config.merge(row.config if row else {}, changes)
    except config.Invalid as exc:
        raise ValidationError({exc.path or 'changes': [exc.message]}) from exc
    if not diff:
        return Written({}, [], None)
    row = row or ProposalConfig.objects.create(deal=deal)
    owners = {config.card_of(path) for path in diff} - {None}
    cleared = _take_off(row, marks.cleared_by(row.marks, owners))
    row.config = merged
    row.updated_by = user if getattr(user, 'is_authenticated', False) else None
    row.save(update_fields=['config', 'marks', 'updated_by', 'updated_at'])
    change = activity.change(target(deal.id), {**diff, **cleared})
    written = activity.record(
        deal, user, AREA, 'updated', 'Edited', len(diff), f'proposal:{deal.id}', 'proposal setting', changes=[change]
    )
    return Written({path: after for path, (_before, after) in diff.items()}, sorted(cleared), written)


def _card_words(card, line):
    title = catalog.CARD_TITLES[card]
    return f'{title} ({lines.label(line)})' if line else title


@transaction.atomic
def set_mark(user, deal, card, line, done, on_proposal):
    """Mark a card completed (`done=True`) or take the mark off. `on_proposal`: the lines the builder shows, which a
    line card must name. Returns (the stamp or None, Activity row or None)."""
    if card not in catalog.CARDS:
        raise ValidationError({'card': [marks.NO_CARD.format(card=card)]})
    if not isinstance(done, bool):
        raise ValidationError({'done': ['done must be true or false.']})
    line = (line or None) if card in catalog.LINE_CARDS else None
    if card in catalog.LINE_CARDS and line not in on_proposal:
        raise ValidationError({'line': [f'This deal has no "{line or ""}" line on its proposal.']})
    deal, row = _locked(deal.pk)
    before = marks.stamp_of(row.marks, card, line) if row else None
    if bool(before) == done:
        return before, None
    row = row or ProposalConfig.objects.create(deal=deal)
    after = marks.stamp(user, clock.now().isoformat()) if done else None
    key = _mark_key(marks.path(card, line))
    if after:
        config.place(row.marks, key, after)
    else:
        config.drop(row.marks, key)
    row.save(update_fields=['marks', 'updated_at'])
    verb = 'Marked' if done else 'Took the completed mark off'
    summary = f'{verb} {_card_words(card, line)}{" completed" if done else ""}'
    change = activity.change(target(deal.id), {marks.path(card, line): [before, after]})
    return after, activity.record(deal, user, AREA, MARKED, summary, changes=[change])


def clear_marks(deal_id, line_keys, cards=('quotes',)):
    """Take the marks of `cards` off `line_keys` in one UPDATE (`#-` per path); no Activity."""
    paths = [['lines', line, card] for line in sorted(set(line_keys)) if line in lines.BY_KEY for card in cards]
    if not paths:
        return 0
    sql = '"marks"' + ' #- %s::text[]' * len(paths)
    return ProposalConfig.objects.filter(deal_id=deal_id).update(marks=RawSQL(sql, paths))


def on_plans_changed(sender, **kwargs):
    """quotes' `plans_changed` receiver (O.1): the lines' Plans card marks come off."""
    clear_marks(kwargs['deal_id'], kwargs['lines'])
