"""Using an intake read, and ↶ Undo this run (plan.md §5.2, §10.5; B40, D72, D73, D112; slice 51): the intake reader's
`apply` and `undo`.

`apply(user, deal, job, select=None, picks=None)` lands the chosen parts of the read's change set (`select`: item ids;
None: the ticked ones) in landing.apply's transaction, which locked the Deal and the job:
- new contacts first, through deals' contact service (the Client is to the left in the chain, so its lock comes
  first); their rows keep keys only, as every contact write's do;
- then the answers and the coverage lines under the Intake row's lock, in one Activity row (area intake, action
  `read`, "Used Claude's read: 5 intake answers, 1 coverage line") with before and after per key: each answer through
  `deals.values.apply` with origin `ai`, its file, page or cell, what was read (so None puts it back, §3.7) and
  Claude's doubt (`low`, OQ28's flag); the deal's effective date through its one door; a coverage line the deal lacks
  is added, and an existing line's blanks are filled.
A value that changed since the read was made is left out and said (`skipped`), never written over.
`undo(user, deal, job, force=False)` reverts the landing's intake row through intake's reverter (refused after a later
write to one of its keys; with `force`, that is said and the rest goes back) and removes the contacts it added, unless
someone edited them since.
"""

import datetime

from django.db import transaction

from deals import activity, clock
from deals.models import Activity, Contact
from deals.services import set_effective_date
from deals.services.contacts import create_contact, delete_contact
from deals.values import apply as apply_values
from deals.values import source

from .. import flags, form
from ..models import CurrentCoverage, Intake
from ..reader.changes import same
from ..selectors import answers_of
from ..signals import announce
from . import rows

ACTION = 'read'
CHANGED = '{label} changed since the read, so it was left as it is.'
ADDED_SINCE = 'The deal gained a {label} coverage line since the read, so its line was left as it is.'


def _plural(count, one, many):
    return f'{count} {one if count == 1 else many}'


def _chosen(job, select):
    items = (job.result or {}).get('items') or []
    if select is None:
        return [item for item in items if item.get('tick')]
    wanted = {str(ref) for ref in select}
    return [item for item in items if item['id'] in wanted]


def _contacts(user, deal, items):
    made = []
    for item in items:
        fields = {key: item[key] for key in ('name', 'title', 'email', 'phone') if item.get(key)}
        if item.get('role'):
            fields['role'] = item['role']
        made.append(create_contact(user, deal.client_id, **fields).id)
    return made


def _source(user, item):
    """An answer's source: what the producer said in a chat is their own hand edit (B39, D85); anything else is
    Claude's, with its file and page or cell, what was read and its doubt."""
    if item.get('dictated'):
        return source('typed', user)
    return source(
        'ai',
        user,
        doc=item.get('doc'),
        page=item.get('page'),
        cell=item.get('cell'),
        low=item.get('low'),
        read_value=item['new'],
    )


def _answers(user, deal, intake, items, skipped):
    """(the entries the answers wrote, the Intake row)."""
    answers = answers_of(deal, intake)
    sources = dict(intake.sources) if intake else {}
    wanted, entries = {}, {}
    for item in items:
        if not same(answers.get(item['key']), item['old']):
            skipped.append(CHANGED.format(label=item['label']))
            continue
        wanted[item['key']] = item['new']
        entries[item['key']] = _source(user, item)
    changed = apply_values(answers, sources, wanted, lambda key: entries[key])
    if not changed:
        return [], intake
    out = []
    if form.EFFECTIVE_DATE in changed:
        moved = set_effective_date(deal.id, datetime.date.fromisoformat(changed[form.EFFECTIVE_DATE][1]))
        out.append(activity.change(f'deal:{deal.id}', moved))
    intake = intake or Intake.objects.create(deal_id=deal.id)
    intake.answers = {key: value for key, value in answers.items() if key != form.EFFECTIVE_DATE}
    intake.sources = sources
    flags.stamp(deal, intake)
    intake.save(update_fields=['answers', 'sources', 'flags', 'updated_at'])
    kept = {key: pair for key, pair in changed.items() if key != form.EFFECTIVE_DATE}
    if kept:
        out.insert(0, activity.change(rows.intake_target(deal.id), kept))
    return out, intake


def _coverage(deal, items, skipped):
    out = []
    by_id = {row.id: row for row in rows.lock_coverage(deal.id, [i['coverage'] for i in items if i['coverage']])}
    lines = set(CurrentCoverage.objects.filter(deal=deal).values_list('line', flat=True))
    for item in items:
        values = {value['key']: value['new'] for value in item['values']}
        if 'renewal_date' in values:
            values['renewal_date'] = datetime.date.fromisoformat(values['renewal_date'])
        if item['coverage'] is None:
            if item['line'] in lines:
                skipped.append(ADDED_SINCE.format(label=item['label']))
                continue
            row = CurrentCoverage.objects.create(
                deal_id=deal.id, line=item['line'], sort_order=rows.next_sort_order(deal.id), **values
            )
            out.append(activity.change(rows.target(row.id), rows.created(row)))
            continue
        row = by_id.get(item['coverage'])
        if row is None:
            continue
        before = rows.state(row)
        for key, value in values.items():
            if not getattr(row, key):  # blanks only: what a person wrote there since stays
                setattr(row, key, value)
        changed = rows.changed(before, row)
        if changed:
            row.save(update_fields=list(changed))
            out.append(activity.change(rows.target(row.id), changed))
    return out


def _contact_rows(contact_ids):
    if not contact_ids:
        return []
    found = []
    for contact_id in contact_ids:
        row = Activity.objects.filter(area='contacts', changes__contains=[{'t': f'contact:{contact_id}'}])
        found += list(row.order_by('id').values_list('id', flat=True)[:1])
    return found


def land(user, deal, items, *, by_claude=False):
    """(the Activity row or None, [what it wrote, in words], [skipped sentences]): the chosen answers and coverage
    lines in one intake row, under the Intake row's lock. `by_claude`: a chat turn's changes (B39; slice 24's rule):
    Claude's own row, never merged, so ↶ Undo this run takes back only them."""
    skipped = []
    intake = Intake.objects.select_for_update().filter(deal_id=deal.id).first()
    entries, intake = _answers(user, deal, intake, [item for item in items if item['op'] == 'answer'], skipped)
    covered = _coverage(deal, [item for item in items if item['op'] == 'coverage'], skipped)
    answered = sum(len(entry['k']) for entry in entries if entry['t'].startswith('intake:'))
    answered += sum(1 for entry in entries if entry['t'].startswith('deal:'))
    parts = [
        _plural(answered, 'intake answer', 'intake answers') if answered else '',
        _plural(len(covered), 'coverage line', 'coverage lines') if covered else '',
    ]
    parts = [part for part in parts if part]
    row = None
    if entries or covered:
        words = ', '.join(parts)
        row = activity.record(
            deal,
            user,
            rows.AREA,
            'chat' if by_claude else ACTION,
            f'Claude edited {words}' if by_claude else f"Used Claude's read: {words}",
            changes=entries + covered,
            actor_kind='claude' if by_claude else None,
        )
    if covered:
        announce(deal.id)  # the lines in force moved: census's required columns follow
    return row, parts, skipped


def apply(user, deal, job, select=None, picks=None):
    """What the landing wrote: {activity_id, activity_ids, areas, summary, skipped, plan_ids, contacts}."""
    chosen = _chosen(job, select)
    contact_ids = _contacts(user, deal, [item for item in chosen if item['op'] == 'contact'])
    row, parts, skipped = land(user, deal, chosen)
    if contact_ids:
        parts.append(_plural(len(contact_ids), 'contact', 'contacts'))
    ids = ([row.id] if row else []) + _contact_rows(contact_ids)
    return {
        'activity_id': row.id if row else (ids[0] if ids else None),
        'activity_ids': ids,
        'areas': ['intake', 'activity'],
        'summary': ' · '.join(parts) or 'nothing new for Intake',
        'skipped': skipped,
        'plan_ids': [],
        'contacts': contact_ids,
    }


def undo(user, deal, job, force=False):
    """↶ Undo this run: {reverted, kept, skipped, at, by}."""
    landed = (job.result or {}).get('landed') or {}
    reverted, kept, skipped = [], [], []
    for row_id in sorted(landed.get('activity_ids') or [], reverse=True):
        row = Activity.objects.filter(pk=row_id, deal_id=deal.id).first()
        if row is None or row.area != rows.AREA or row.reverted_at is not None:
            continue
        try:
            with transaction.atomic():
                reverted.append(activity.revert(row_id, user).id)
        except activity.Refused as exc:
            if not force:
                raise
            skipped.append(exc.sentence)
    for contact_id in landed.get('contacts') or []:
        if not Contact.objects.filter(pk=contact_id).exists():
            continue
        edited = Activity.objects.filter(
            area='contacts', action='updated', changes__contains=[{'t': f'contact:{contact_id}'}]
        ).exists()
        if edited:
            kept.append('a contact edited since')
        else:
            delete_contact(user, contact_id)
    return {'reverted': reverted, 'kept': kept, 'skipped': skipped, 'at': clock.now().isoformat(), 'by': user.id}
