"""The Work queue's rows (I70, I71, I73–I77, I80, I122; old serializers/radar.py `work_feed_payload`). Pure: built from
the facts, the steps and the marks the deal's own Agenda reads, so a row's next step is the tab's (I68).

Every row carries the deal's facts the browser filters and sorts on, worked out here (ch. 12): `client_id`,
`client_name`, `client_status` (the client's status today: Prospects lists only Prospect rows, so a sale moves the row
to Clients at once; I122 as changed by OQ101 c, OQ91), `type` (the deal type as of the deal, I123), `stage`, `due` and
`due_in` (days from the agency's today, negative when overdue), `owner_id` and `owner_name` (the deal's owner, else
the client's; a task's assignee, I73), `deal_size` (exact text), `link` (what the row opens), `home` (what the name
opens), `held` (the day a Later mark gives the row back, or None), `finished` and `lost`.

- deal rows: the next step's words, severity and link; `progress_pct` (milestones done over those that apply, I69);
  `steps`, every open step for "All open steps" (I74; old `feed_steps`: ours to do now, never waiting or blocked);
  `response`, the Client response column (L118; D-159), and `review_link`;
- task rows: an open hand task (I71), on a sold or lost deal too, opening the deal's Agenda at the task;
- nudge rows: a review link's open reminder (I35), filed under Tasks as before (ch. 21), opening the link's settings.
"""

from .. import catalogue, journey, links, rows, rules


def _due(day, today):
    return {'due': day, 'due_in': rules.due_in(day, today)}


def response(review):
    """The Client response column (L118; old D-159 `client_responses`): None until the client has reached out on a
    link — answered, still typing, or asked — else {state, questions, answers, answering, who, at, kind}. `waiting`:
    something they sent waits on us; `answering`: someone is still typing; `answered`: everything is handled."""
    review = review or {}
    found = review.get('response') or {}
    questions = (review.get('questions') or {}).get('open', 0) or 0
    answers = (review.get('pending') or {}).get('total', 0) or 0
    answering = len(review.get('in_progress') or [])
    reached = found.get('state') in ('answered', 'answering')
    if not (reached or questions or answers):
        return None
    if questions or answers:
        state = 'waiting'
    else:
        state = 'answering' if answering else 'answered'
    kind = 'asked' if questions and not answers else 'submitted' if found.get('state') == 'answered' else 'answered'
    at = found.get('at') if reached else (review.get('questions') or {}).get('oldest_at')
    return {
        'state': state,
        'questions': questions,
        'answers': answers,
        'answering': answering,
        'who': found.get('name') or '',
        'at': at.isoformat() if hasattr(at, 'isoformat') else at,
        'kind': kind,
    }


def open_steps(marked, deal_id, today):
    """The deal's steps ours to do now (I74), each with its link, its own due day (`due_in` from the agency's today)
    and its Later day."""
    return [
        {
            'id': step['id'],
            'key': step['key'],
            'label': step['label'],
            'severity': step['severity'],
            'link': links.link_for(deal_id, step['tab'], step.get('params')),
            'due': step.get('due'),
            'due_in': rules.due_in(step.get('due'), today),
            'later_until': step.get('later_until'),
            'wait_days': step.get('wait_days'),
        }
        for step in marked
        if step['state'] == 'open'
    ]


def deal_row(base, facts, unmarked, marked, next_step, today):
    """One deal's row: `base` holds its deals facts (above); `next_step` is `selectors.next_of`'s answer."""
    lost = facts['deal']['lost']
    deal_id = base['deal_id']
    found = next_step or {'key': None, 'label': catalogue.COMPLETE, 'severity': 'done', 'link': None}
    progress = 0 if lost else journey.progress(journey.journey(facts, unmarked))['pct']
    held = found.get('later_until')
    return {
        **base,
        'kind': 'deal',
        'id': f'deal:{deal_id}',
        'category': catalogue.PIPELINE['key'],
        'key': found.get('key'),
        'label': found['label'],
        'severity': 'lost' if lost else found.get('severity') or 'info',
        'link': found.get('link') or base['home'],
        **_due(base['effective_date'], today),
        'held': held.isoformat() if hasattr(held, 'isoformat') else held,
        'finished': lost or rows.finished(unmarked),
        'lost': lost,
        'progress_pct': progress,
        'steps': [] if lost else open_steps(marked, deal_id, today),
        'response': None if lost else response(facts.get('review')),
        'review_link': links.link_for(deal_id, 'review'),
    }


def task_row(base, task, today, assignee):
    """An open hand task (I71): `assignee` is {id, name} or None (the row then shows the deal's owner, I73)."""
    due = task.due.isoformat()
    return {
        **base,
        'kind': 'task',
        'id': f'task:{task.id}',
        'task_id': task.id,
        'category': catalogue.TASKS,
        'key': None,
        'label': task.title,
        'severity': rules.severity(task.due, today),
        'link': links.focus(base['deal_id'], f'task:{task.id}'),
        **_due(due, today),
        'owner_id': assignee['id'] if assignee else base['owner_id'],
        'owner_name': assignee['name'] if assignee else base['owner_name'],
        'held': None,
        'finished': False,
        'lost': base['stage'] == 'lost',
    }


def nudge_row(base, nudge, today):
    """A review link's open reminder (I35), under Tasks (ch. 21); it opens that link's settings card."""
    return {
        **base,
        'kind': 'nudge',
        'id': f'nudge:{nudge["link_id"]}',
        'link_id': nudge['link_id'],
        'category': catalogue.TASKS,
        'key': None,
        'label': catalogue.NUDGE_TITLE.format(who=nudge['who']),
        'severity': rules.severity(nudge['on'], today),
        'link': links.nudge(base['deal_id'], nudge['link_id']),
        **_due(nudge['on'], today),
        'held': None,
        'finished': False,
        'lost': False,
    }
