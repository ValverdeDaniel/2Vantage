"""The Activity log, Revert and access logging (plan.md §3.7, §3.8, O.3.2).

`changes` holds before and after per key and target: [{"t": "plan:41", "k": {"rate_ee": ["612.50", "640"]}}];
a key-only row (census rows, sensitive questionnaire slots, lasers) keeps the keys alone: {"t": ..., "k": ["dob"]}.

Consecutive writes by the same actor with the same `coalesce_key` within 10 minutes merge into the deal's latest row,
which keeps each key's first "before" and last "after" and counts the writes ("Edited 14 plan values"). Review marks,
imports, issues, sales, stage and client-status changes never merge.

Revert (`revert`) calls the area's entry in `reverters`, filled by each owning app in AppConfig.ready(), in one
transaction and the lock order: the Deal, then the owner's rows by id, then this row. It works once.
"""

from datetime import timedelta

from django.db import transaction
from django.db.models import F, Q
from rest_framework import status
from rest_framework.exceptions import APIException

from . import clock
from .models import Activity, Deal

WINDOW = timedelta(minutes=10)
ACCESS = ('downloaded', 'viewed')  # §3.8: never "Last updated", never in the feed
NEVER_MERGE = {'marked', 'imported', 'issued', 'sold', 'stage', 'converted', 'prospect', 'status', 'reverted', *ACCESS}
NOT_REVERTIBLE = {'created', 'deleted', 'reverted', 'sold', 'issued', *ACCESS}

ALREADY_UNDONE = 'This change was already undone.'
KEYS_ONLY = (
    'Only which values changed was recorded here, not the values themselves, so this change cannot be reverted. '
    "Use the grid's Undo right after an edit, or type the earlier values."
)
NOTHING_TO_PUT_BACK = 'This entry has no earlier values to put back.'
NO_REVERTER = 'Changes of this kind cannot be reverted.'
NOT_A_REVERT = 'A revert cannot itself be reverted. Change the values again instead.'
STILL_CHANGING = 'This change was extended while you were reverting it. Open the activity again and retry.'

# {area: fn(activity, user) -> changes it wrote}. The function locks its rows by id, refuses with `Refused`
# (sold plans, signed forms, later writes) and writes the "before" values back through its own services.
reverters = {}


class Refused(APIException):
    """A refused action: 409 with a sentence for the person, and the keys it concerns when there are some."""

    status_code = status.HTTP_409_CONFLICT
    default_code = 'refused'

    def __init__(self, sentence, keys=()):
        self.sentence, self.keys = sentence, list(keys)
        super().__init__({'detail': sentence, 'keys': self.keys} if self.keys else sentence)


def _plural(count, noun):
    return noun if count == 1 else (noun[:-1] + 'ies' if noun.endswith('y') else noun + 's')


def _counted(summary, count, noun):
    return f'{summary} {count} {_plural(count, noun)}'.strip()[:300]


def change(target, diff):
    """One `changes` entry from a {key: [before, after]} diff (as values.apply returns it)."""
    return {'t': target, 'k': diff}


def _clean(changes, keys_only):
    out = []
    for entry in changes or []:
        keys = entry['k']
        if isinstance(keys, dict):
            keys = {key: list(pair) for key, pair in keys.items() if pair[0] != pair[1]}
        if keys_only or isinstance(keys, list):
            keys = sorted(set(keys))
        if keys:
            out.append({'t': str(entry['t']), 'k': keys})
    return out


def merge(first, then):
    """Two change lists as one: each key keeps its first "before" and last "after"; a key back where it began goes."""
    merged, order = {}, []
    for entry in [*first, *then]:
        target, keys = entry['t'], entry['k']
        if target not in merged:
            merged[target] = list(keys) if isinstance(keys, list) else {k: list(v) for k, v in keys.items()}
            order.append(target)
        elif isinstance(merged[target], list) or isinstance(keys, list):
            merged[target] = sorted(set(merged[target]) | set(keys))
        else:
            for key, (before, after) in keys.items():
                merged[target][key] = [merged[target][key][0] if key in merged[target] else before, after]
    return _clean([{'t': t, 'k': merged[t]} for t in order], keys_only=False)


def holds_keys_only(changes):
    return any(isinstance(entry['k'], list) for entry in changes)


def _revertible(changes, action):
    return bool(changes) and not holds_keys_only(changes) and action not in NOT_REVERTIBLE


def _scope(deal_id, subject):
    return (
        {'deal_id': deal_id, 'subject': subject} if deal_id is not None else {'deal__isnull': True, 'subject': subject}
    )


def _merge_into_latest(scope, user, kind, coalesce_key, summary, count, noun, changes, now):
    latest = Activity.objects.filter(**scope).exclude(action__in=ACCESS).order_by('-updated_at', '-id').first()
    if not (
        latest
        and latest.coalesce_key == coalesce_key
        and latest.actor_id == getattr(user, 'id', None)
        and latest.actor_kind == kind
        and latest.reverted_at is None
        and now - latest.updated_at <= WINDOW
    ):
        return None
    merged, total = merge(latest.changes, changes), latest.count + count
    # Conditional, so a revert or another merge that got there first is never overwritten.
    updated = Activity.objects.filter(pk=latest.pk, updated_at=latest.updated_at, reverted_at__isnull=True).update(
        count=total,
        updated_at=now,
        summary=_counted(summary, total, noun),
        changes=merged,
        revertible=_revertible(merged, latest.action),
    )
    if not updated:
        return None
    latest.refresh_from_db()
    return latest


def record(
    deal,
    actor,
    area,
    action,
    summary,
    count=1,
    coalesce_key='',
    noun='',
    *,
    changes=None,
    keys_only=False,
    document_id=None,
    actor_kind=None,
    subject='',
    reverts=None,
    revertible=True,
):
    """Append (or extend) an Activity row and return it.

    `changes` is a list of `change(target, diff)` entries; `keys_only=True` keeps their keys and drops every value.
    With `coalesce_key`, `noun` builds the summary: "Edited 14 plan values".
    `revertible=False` stores a row whose change Revert refuses with the owner's sentence (a status a sale set).
    """
    changes = _clean(changes, keys_only)
    now = clock.now()
    user = actor if getattr(actor, 'is_authenticated', False) else None
    kind = actor_kind or ('user' if user else 'system')
    if action in NEVER_MERGE:
        coalesce_key = ''
    if coalesce_key:
        args = (user, kind, coalesce_key, summary, count, noun, changes, now)
        row = _merge_into_latest(_scope(getattr(deal, 'id', None), subject), *args)
        if row:
            return row
        summary = _counted(summary, count, noun)
    return Activity.objects.create(
        deal=deal,
        subject=subject,
        actor=user,
        actor_kind=kind,
        area=area,
        action=action,
        summary=summary[:300],
        changes=changes,
        revertible=revertible and _revertible(changes, action) and reverts is None,
        document_id=document_id,
        count=count,
        coalesce_key=coalesce_key,
        reverts=reverts,
        created_at=now,
        updated_at=now,
    )


def log_access(deal, user, action, what, document_id, area='documents'):
    """A `downloaded` or `viewed` row (§3.8, E99). `what` names the kind ("a census document"), never a file name.

    Views coalesce per file and person; these rows never move "Last updated" and the feed skips them.
    """
    if action not in ACCESS:
        raise ValueError(f'Not an access action: {action}')
    now = clock.now()
    user = user if getattr(user, 'is_authenticated', False) else None
    key = f'viewed:{document_id}' if action == 'viewed' else ''
    if key:
        views = Activity.objects.filter(deal=deal, action='viewed', coalesce_key=key, actor=user)
        latest = views.order_by('-id').first()
        if latest and now - latest.updated_at <= WINDOW:
            Activity.objects.filter(pk=latest.pk).update(count=F('count') + 1, updated_at=now)
            latest.refresh_from_db()
            return latest
    verb = 'Downloaded' if action == 'downloaded' else 'Viewed'
    return Activity.objects.create(
        deal=deal,
        actor=user,
        actor_kind='user' if user else 'system',
        area=area,
        action=action,
        summary=f'{verb} {what}'[:300],
        document_id=document_id,
        coalesce_key=key,
        created_at=now,
        updated_at=now,
    )


def later_keys(row):
    """{(target, key)} of this row's keys that a later row on the same deal wrote (reverters refuse on these)."""
    mine = {(entry['t'], key) for entry in row.changes for key in entry['k']}
    if not mine:
        return set()
    touching = Q()
    for target in {entry['t'] for entry in row.changes}:
        touching |= Q(changes__contains=[{'t': target}])
    later = (
        Activity.objects.filter(**_scope(row.deal_id, row.subject), pk__gt=row.pk)
        .exclude(action__in=ACCESS)
        .filter(touching)
        .values_list('changes', flat=True)
    )
    return {(entry['t'], key) for changes in later for entry in changes for key in entry['k']} & mine


def changed_since(labels, keys):
    """The 409 for a Revert after a later write, naming what changed: "Rate — EE was changed after this, …"."""
    labels = list(dict.fromkeys(labels))
    names = labels[0] if len(labels) == 1 else ', '.join(labels[:-1]) + ' and ' + labels[-1]
    verb = 'was' if len(labels) == 1 else 'were'
    return Refused(f'{names} {verb} changed after this, so this change cannot be reverted.', keys)


def _refusal(row):
    if row.reverted_at is not None:
        return ALREADY_UNDONE
    if row.reverts_id is not None:
        return NOT_A_REVERT
    if holds_keys_only(row.changes):
        return KEYS_ONLY
    if not row.changes or row.action in NOT_REVERTIBLE:
        return NOTHING_TO_PUT_BACK
    if row.area not in reverters:
        return NO_REVERTER
    return None


def can_revert(row):
    """For lists, without loading `changes`: the stored flag, not yet undone, and an owner that reverts."""
    return row.revertible and row.reverted_at is None and row.reverts_id is None and row.area in reverters


@transaction.atomic
def revert(activity_id, user):
    """Put back the "before" values of one row. Returns the new row (its `reverts` is the old one).

    Raises Activity.DoesNotExist for an unknown id and `Refused` (409) with a sentence otherwise.
    """
    deal_id = Activity.objects.values_list('deal_id', flat=True).get(pk=activity_id)
    if deal_id is not None:
        Deal.objects.select_for_update().only('id').get(pk=deal_id)  # lock order: the Deal first
    row = Activity.objects.get(pk=activity_id)
    refusal = _refusal(row)
    if refusal:
        raise Refused(refusal)
    written = reverters[row.area](row, user)
    claimed = Activity.objects.filter(pk=row.pk, reverted_at__isnull=True, updated_at=row.updated_at).update(
        reverted_at=clock.now(), reverted_by=user if getattr(user, 'is_authenticated', False) else None
    )
    if not claimed:
        raise Refused(ALREADY_UNDONE if Activity.objects.get(pk=row.pk).reverted_at else STILL_CHANGING)
    return record(
        row.deal,
        user,
        row.area,
        'reverted',
        f'Reverted: {row.summary}',
        changes=written,
        document_id=row.document_id,
        subject=row.subject,
        reverts=row,
    )
