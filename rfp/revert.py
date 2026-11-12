"""Revert of an RFP Activity row (plan.md §3.7, O.3.2; K115): a burst of settings edits, a card's mark, or a send (slice
46: `sends.<draft>` put back as it was, the route a first send pinned with it; the stage a first send moved stays,
forward only).
Registered as `activity.reverters['rfp']` in RfpConfig.ready().

`deals.activity.revert` has already locked the Deal; this locks the RfpRequest row. It refuses after a later write to
one of the row's keys (naming it), and otherwise puts each key's "before" back: a setting onto the row, a mark
(`done.<card>`) into `done`. Putting back the carriers, "Other carriers" or the ticks rewrites census's stored counts
on commit, as the edit did (K124). Notes rows name the key only, so `deals.activity` refuses them before this runs.
"""

from deals import activity

from . import cleaners, drafts, services
from .models import RfpRequest

WORDS = {
    'route': 'The route',
    'carriers': 'The carriers',
    'other_carriers': 'Other carriers',
    'funding': 'The funding to quote',
    'due_date': 'Quotes due back',
    'notes': 'The notes for the carriers',
    'include': 'The packet’s ticks',
    'form': 'The request form',
}


def label(key):
    if key.startswith('done.'):
        card = key.removeprefix('done.')
        return f'The completed mark on {services.CARD_TITLES.get(card, card)}'
    if key.startswith('sends.'):
        return f'The {drafts.label_of(key.removeprefix("sends."))} email’s send'
    return WORDS.get(key, key)


def revert(row, user):  # noqa: ARG001 (the reverters' signature)
    later = activity.later_keys(row)
    if later:
        keys = sorted(later)
        raise activity.changed_since([label(key) for _target, key in keys], [key for _target, key in keys])
    stored = RfpRequest.objects.select_for_update().get(deal_id=row.deal_id)
    now = cleaners.stored(stored)
    written, settings, fields = [], {}, set()
    for entry in row.changes:
        diff = {}
        for key, (before, _after) in entry['k'].items():
            if key.startswith('done.'):
                card = key.removeprefix('done.')
                diff[key] = [(stored.done or {}).get(card), before]
                marks = {name: stamp for name, stamp in (stored.done or {}).items() if name != card}
                stored.done = {**marks, card: before} if before else marks
                fields.add('done')
            elif key.startswith('sends.'):
                draft = key.removeprefix('sends.')
                diff[key] = [(stored.sends or {}).get(draft), before]
                others = {name: send for name, send in (stored.sends or {}).items() if name != draft}
                stored.sends = {**others, draft: before} if before else others
                fields.add('sends')
            else:
                diff[key] = [now[key], before]
                settings[key] = before
                fields.add(key)
        written.append(activity.change(entry['t'], diff))
    services.put(stored, settings)
    stored.save(update_fields=[*sorted(fields), 'updated_at'])
    if fields & set(services.REQUIRES):
        services.refresh_census_on_commit(row.deal_id)
    return written
