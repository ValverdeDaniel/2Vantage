"""Which parts of a quote read's change set a person chose to use (plan.md §10.5; D28, D31, D72, D117). Pure.

"Use this scan ▸" sends nothing: the read lands as it was proposed, every ticked item with its ticked values, its
"replaces" only when the reader was sure (D115), never a printed count (D67) or a plan the person must place (D117).
"Apply N selected ▸" sends `select`: the ids of the items to use, and "<item>:<key>" for a value that arrived unticked
(left alone, or one Claude was unsure of) that the person wants anyway, or "<item>:replaces" for an unsure link.
`picks` says where each "Which current plan?" item goes: a current plan's id (its values fill that plan), "new" (one
more current plan) or "alternate" (the incumbent's extra option, D117). A "Which current plan?" item chosen without a
pick goes to the first plan the read named.
"""

from collections import namedtuple

from rest_framework.exceptions import ValidationError

PLAN_OPS = ('create_plan', 'set_values', 'pick_current')
NEW, ALTERNATE = 'new', 'alternate'

BAD_SELECT = 'Send the ticked items as a list of their ids.'
UNKNOWN = 'These are not part of this read: {ids}.'
NOTHING = 'Tick something to use, or discard the read.'
BAD_PICKS = 'Send each "Which current plan?" choice as {item id: plan id, "new" or "alternate"}.'
BAD_PICK = '{name}: pick one of the current plans the read named, a new current plan, or an alternate.'

# item: the change-set item; values: the values that land; replaces: its link lands; pick: where a pick goes.
Chosen = namedtuple('Chosen', 'item values replaces pick')


def _ids(select, items):
    if not isinstance(select, list) or not all(isinstance(entry, str) for entry in select):
        raise ValidationError({'select': [BAD_SELECT]})
    known = {item['id'] for item in items}
    unknown = sorted({entry.partition(':')[0] for entry in select} - known)
    if unknown:
        raise ValidationError({'select': [UNKNOWN.format(ids=', '.join(unknown))]})
    if not select:
        raise ValidationError({'select': [NOTHING]})
    return set(select)


def _pick(item, picks):
    raw = picks.get(item['id'])
    options = [option['plan'] for option in item.get('options') or [] if option.get('plan')]
    if raw in (None, ''):
        return options[0] if options else NEW
    if raw in (NEW, ALTERNATE):
        return raw
    try:
        plan_id = int(raw)
    except (TypeError, ValueError):
        plan_id = None
    if plan_id not in options:
        raise ValidationError({'picks': [BAD_PICK.format(name=f'{item["carrier"]} {item["name"]}')]})
    return plan_id


def choose(change_set, select=None, picks=None):
    """[Chosen] in the read's order (F138): the plan items, the printed counts and the lines to add that land."""
    items = list((change_set or {}).get('items') or [])
    if picks is not None and not isinstance(picks, dict):
        raise ValidationError({'picks': [BAD_PICKS]})
    picks = {str(key): value for key, value in (picks or {}).items()}
    wanted = _ids(select, items) if select is not None else None
    out = []
    for item in items:
        if wanted is None:
            if not item.get('tick') or item.get('stale') or item['op'] == 'pick_current':
                continue
        elif item['id'] not in wanted:
            continue
        values = [
            value
            for value in item.get('values') or []
            if value.get('tick') or (wanted is not None and f'{item["id"]}:{value["key"]}' in wanted)
        ]
        link = item.get('replaces') or {}
        replaces = bool(link.get('to')) and (
            bool(link.get('tick')) or (wanted is not None and f'{item["id"]}:replaces' in wanted)
        )
        pick = _pick(item, picks) if item['op'] == 'pick_current' else None
        out.append(Chosen(item, values, replaces, pick))
    return out


def plan_items(chosen):
    return [entry for entry in chosen if entry.item['op'] in PLAN_OPS]


def of_op(chosen, op):
    return [entry for entry in chosen if entry.item['op'] == op]
