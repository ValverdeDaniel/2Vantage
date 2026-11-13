"""One deal's Agenda rows as the tab reads them (I4–I40; plan.md §7.15). Each row carries its `section`, the `date` its
column shows, its `link` (Open ▸) and `can`: which buttons it offers, so the browser holds no rule of its own (I20).

- step rows: the marked steps with their Later and Done anyway overlays (I10–I26);
- task rows: tasks added by hand, open and done (I27–I34); deleting is for the creator or an admin (OQ93);
- nudge rows: a review link's reminder (I35–I39). Later and ✓ on them go through review's `set_nudge` and
  `finish_nudge` (I37), which slice 57 builds; until then a nudge row offers only Open ▸.
`arrange` orders them (I6): open tasks and nudges by date, then open steps in catalogue order; then Waiting on,
Later and Blocked in catalogue order; Done last, steps before tasks.
"""

from . import catalogue, links, rows, rules


def _name(user):
    return (user.get_full_name() or user.username) if user else ''


def step_row(step, deal_id):
    live = rows.live(step)
    marked = bool(step.get('later_until') or step.get('done_anyway'))
    also = step.get('also')
    return {
        **{key: value for key, value in step.items() if key not in ('also', 'params')},
        'section': rows.section(step),
        'date': step.get('due'),
        'link': links.link_for(deal_id, step['tab'], step.get('params')),
        'also': {'label': also['label'], 'link': links.link_for(deal_id, also['tab'])} if also else None,
        'chip': None,
        'can': {
            'later': live and not marked,
            'done_anyway': live and not marked and rules.can_done_anyway(step['key']),
            'follow_up': live and not marked and rules.is_follow_up(step['key']),
            'bring_back': bool(step.get('later_until')),
            'undo': bool(step.get('done_anyway')),
        },
    }


def can_delete(task, viewer):
    return bool(getattr(viewer, 'is_staff', False) or (task.created_by_id and task.created_by_id == viewer.id))


def task_row(task, today, viewer):
    row = {
        'id': f'task:{task.id}',
        'kind': 'task',
        'task_id': task.id,
        'key': f'task:{task.id}',
        'label': task.title,
        'title': task.title,
        'due': task.due.isoformat(),
        'date': task.due.isoformat(),
        'note': task.note,
        'assigned_to': {'id': task.assigned_to_id, 'name': _name(task.assigned_to)} if task.assigned_to_id else None,
        'done': task.done,
        'done_at': task.done_at.isoformat() if task.done_at else None,
        'done_by': _name(task.done_by),
        'created_by': {'id': task.created_by_id, 'name': _name(task.created_by)} if task.created_by_id else None,
        'severity': 'done' if task.done else rules.severity(task.due, today),
        'chip': catalogue.TASK_CHIP,
        'link': None,
        'can': {
            'tick': not task.done,
            'reopen': task.done,
            'later': not task.done,
            'edit': True,
            'delete': can_delete(task, viewer),
        },
    }
    row['section'] = rows.section(row)
    return row


def nudge_row(nudge, deal_id, today):
    done = bool(nudge.get('done_at'))
    row = {
        'id': f'nudge:{nudge["link_id"]}',
        'kind': 'nudge',
        'key': f'nudge:{nudge["link_id"]}',
        'link_id': nudge['link_id'],
        'label': catalogue.NUDGE_TITLE.format(who=nudge['who']),
        'date': nudge['on'],
        'done': done,
        'severity': 'done' if done else rules.severity(nudge['on'], today),
        'chip': catalogue.NUDGE_CHIP,
        'link': None if done else links.link_for(deal_id, 'review'),
        'later_max': nudge.get('later_max'),
        'can': {'tick': False, 'later': False},  # review's set_nudge and finish_nudge (slice 57)
    }
    row['section'] = rows.section(row)
    return row


def arrange(step_rows, task_rows, nudge_rows):
    by_date = sorted([*task_rows, *nudge_rows], key=lambda row: (row['date'] or '', row['id']))
    order = []
    for section in catalogue.SECTION_KEYS:
        if section == 'up_next':
            order += [row for row in by_date if row['section'] == section]
        order += [row for row in step_rows if row['section'] == section]
        if section == 'done':
            order += [row for row in by_date if row['section'] == section]
    return order
