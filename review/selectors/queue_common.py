"""What every review-queue item says, whatever its section (plan.md §8.8; L15, L16, L20; old 891f1b3 `items.py`,
`ReadyWhy.jsx`): its ref, what the answer did (`change`), where it stands (`phase`), why it is ready
(`ready_why`, `idle_days`), whose link it came through (`via`, `link_id`) and when (`at`), and its group (the chips
over the queue: a census column or an intake section, each with its change).
"""

from ..rules import items as item_rules

NOBODY = 'The client'


def via(link):
    return (link.name or NOBODY) if link is not None else NOBODY


def item(entry, links, now, *, change, group, group_label):
    link = links.get(entry.link_id)
    return {
        'ref': entry.ref,
        'change': change,
        'phase': item_rules.phase(link, now),
        'ready_why': item_rules.ready_why(link, now),
        'idle_days': item_rules.idle_days(link, now),
        'link_id': link.id if link is not None else None,
        'via': via(link),
        'at': entry.at,
        'group': group,
        'group_label': group_label,
    }
