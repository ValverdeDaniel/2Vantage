"""What came back, per section, for the section bars and the To review lane (plan.md §8.8; L9, L14, L43, C34; old
891f1b3 `review/items.py` `_client_counts`, `_add`, `_names`). Pure: the waiting entries, their links and `now`.

`counts(entries, links, now)` → {surface: {to_review, in_progress, ready, ready_submitted, ready_idle, names}}:
- `to_review`: answers whose link is ready (submitted after its last save, or idle 24 h); `in_progress`: still typing;
- `ready`: the part of `to_review` "Approve N ready" may take (an answer that blanks a value waits for a person), split
  into `ready_submitted` (what the button takes) and `ready_idle` (what its tick adds);
- `names`: who answered (still typing or ready), the most answers first, each once: the bar's "↩ Dana answered 3". A
  link with no name is left out, and the bar then says "The client";
- `going_back` (slice 56): answers sent back to the client and not answered since (`going`, `rules.tray.going_back`):
  out of `to_review` and `in_progress` until they answer again.
"""

from collections import Counter

from . import items

SURFACES = ('intake', 'census')


def empty():
    return {
        'to_review': 0,
        'in_progress': 0,
        'ready': 0,
        'ready_submitted': 0,
        'ready_idle': 0,
        'going_back': 0,
        'names': [],
    }


def _names(by_link, links):
    ranked = sorted(by_link.items(), key=lambda pair: (-pair[1], links[pair[0]].name or ''))
    return list(dict.fromkeys(links[link_id].name for link_id, _n in ranked if links[link_id].name))


def counts(entries, links, now, going=frozenset()):
    out = {surface: empty() for surface in SURFACES}
    answered = {surface: Counter() for surface in SURFACES}
    for entry in entries:
        found = out.setdefault(entry.surface, empty())
        if entry.ref in going:
            found['going_back'] += 1
            continue
        link = links.get(entry.link_id)
        why = items.ready_why(link, now)
        if not why:
            found['in_progress'] += 1
        else:
            found['to_review'] += 1
            cleared = not entry.person and items.blank(entry.value)
            if not cleared:
                found['ready'] += 1
                found['ready_submitted' if why == items.SUBMITTED else 'ready_idle'] += 1
        if link is not None:
            answered.setdefault(entry.surface, Counter())[link.id] += 1
    for surface, by_link in answered.items():
        out[surface]['names'] = _names(by_link, links)
    return out


def ready_refs(entries, links, now, *, include_idle=False, going=frozenset()):
    """The refs "Approve N ready" takes: ready for their link's reason, not sent back, and not one that blanks a
    value."""
    return [
        entry.ref
        for entry in entries
        if entry.ref not in going
        and items.takes(
            items.ready_why(links.get(entry.link_id), now),
            cleared=not entry.person and items.blank(entry.value),
            include_idle=include_idle,
        )
    ]
