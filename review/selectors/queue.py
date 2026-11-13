"""The review queue (plan.md §7.13 `GET deals/{id}/review/queue/`, §8.8; L11, L15, L16, L20, B38, C32; old 891f1b3
`items.census_client`, `CensusClientReview.jsx`, `IntakeQueue.jsx`): what the client sent on one section, by phase and
group, 50 a page.

`queue(deal, surface, phase=, group=, page=)` → {surface, phase, idle_hours, phases {to_review, in_progress}, groups
[{key, label, change, count}], items [item], ids [ref], page {page, page_count, row_count, has_prev, has_next},
in_progress [{link_id, name, last_saved_at, ready_at}]}.
- `phase`: `to_review` (ready: submitted, or idle 24 h), `in_progress` (still typing: read only until then) or
  `going_back` (sent back to the client and not answered since; slice 56);
- `groups`: the phase's answers by column (census), section (intake) or form and section (questionnaire, slice 58)
  and change, the chips over the queue; `group`
  narrows the items to one, and `ids` holds its refs (all of the phase's when none is picked, at most 5,000) for its
  "Approve all N ✓";
- an item: {ref, kind answer|block|person, label, section?, person?, ours, theirs, change, phase, ready_why,
  idle_days, link_id, via, at, group, group_label, required?, blocks?, details?, editable} (queue_common and each
  section's module), and on the page's items (slice 56) its `thread` (the notes on it, `selectors.notes.payload`),
  `question_open` and `draft_id` (a send-back waiting in the tray).
Reads in a fixed number of queries; writes nothing. Member data rides it, staff only, and never a log (§3.8).
"""

from deals import clock

from ..rules import items as item_rules
from . import entries as entry_rows
from . import going, queue_census, queue_intake, queue_questionnaire
from . import notes as note_rows

PAGE_SIZE = 50
IDS_CAP = 5000
SURFACES = {'intake': queue_intake, 'census': queue_census, 'questionnaire': queue_questionnaire}


def _iso(moment):
    return moment.isoformat() if moment else None


def _groups(items):
    found = {}
    for item in items:
        group = found.setdefault(
            item['group'], {'key': item['group'], 'label': item['group_label'], 'change': item['change'], 'count': 0}
        )
        group['count'] += 1
    return list(found.values())


def _typing(found, links, now):
    ids = dict.fromkeys(entry.link_id for entry in found if entry.link_id in links)
    out = []
    for link_id in ids:
        link = links[link_id]
        if item_rules.phase(link, now) == item_rules.IN_PROGRESS:
            out.append(
                {
                    'link_id': link.id,
                    'name': link.name,
                    'last_saved_at': _iso(link.last_saved_at),
                    'ready_at': _iso(item_rules.ready_at(link, now)),
                }
            )
    return out


def _threads(deal, items):
    threads = note_rows.threads(deal.id, {item['ref'] for item in items})
    for item in items:
        thread = threads.get(item['ref'], [])
        item['thread'] = thread
        item['question_open'] = any(n['kind'] == 'question' and not n['resolved_at'] for n in thread)
        draft = next((n for n in thread if n['kind'] in ('ask', 'sendback') and not n['sent_at']), None)
        item['draft_id'] = draft['id'] if draft else None
    return items


def queue(deal, surface, *, phase=item_rules.TO_REVIEW, group='', page=1, now=None):
    now = now or clock.now()
    found = entry_rows.waiting([deal.id], (surface,)).get(deal.id, [])
    links = entry_rows.links_of(found)
    back = going.refs([deal.id], {deal.id: found}, going.opens_for([deal.id], now))[deal.id]
    every = SURFACES[surface].items(deal, found, links, now)
    for item in every:
        if item['ref'] in back:
            item['phase'] = item_rules.GOING_BACK
    shown = [item for item in every if item['phase'] == phase]
    picked = [item for item in shown if not group or item['group'] == group]
    count = len(picked)
    pages = max(1, -(-count // PAGE_SIZE))
    page = min(max(1, page), pages)
    start = (page - 1) * PAGE_SIZE
    return {
        'surface': surface,
        'phase': phase,
        'idle_hours': int(item_rules.IDLE.total_seconds() // 3600),
        'phases': {name: sum(1 for item in every if item['phase'] == name) for name in item_rules.PHASES},
        'groups': _groups(shown),
        'items': _threads(deal, picked[start : start + PAGE_SIZE]),
        'ids': [item['ref'] for item in picked][:IDS_CAP] if phase == item_rules.TO_REVIEW else [],
        'page': {
            'page': page,
            'page_count': pages,
            'row_count': count,
            'has_prev': page > 1,
            'has_next': page < pages,
        },
        'in_progress': _typing(found, links, now),
    }
