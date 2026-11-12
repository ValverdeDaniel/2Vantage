"""Rank's rules through the star rule (plan.md §5.4, §10.4; D96, F111, OQ44; slice 37; the old pipeline/advisor.py
`rank_case_plans` and `curated_reason` at 891f1b3). Pure, over `shapes.LineData`.

- What Rank replaces: on a whole line, every star on it, hand-picked ones too, as the old Rank did ("Replaces the
  current shortlist on this line, including hand-picked plans"); on a filtered board, only the stars among the plans
  the board shows, so a star outside the filter stays (OQ44, default no; F.5 #11: the old Rank cleared the whole line
  even then). `scope(line, among)` is that set of plans; `cleared(line, scope)` the line with its stars taken off.
- What Rank may star: the quoted plans of the scope (`candidates`), never a current plan (it takes no star).
- `choose(line, picks, scope)`: Claude's picks in Claude's order, each once, at most `MAX_PICKS`, each only while
  `presented.room()` holds it on the cleared line (a pair's two halves take one column; a recommended plan none), so
  Rank never pushes a line past its 16 columns. Returns ([(id, reason)], [ids left out for want of room]).
- `fit(line, scope)`: how many columns Rank may fill, told to Claude up front.
- `reason(text)`: one sentence cut to fit `Plan.star_reason`; `picks_from(answer)` reads Claude's answer.
- `curated(line)`: why someone has already chosen on a line (its stars, a sale, a recommendation), or '': a rank
  after a read leaves such a line alone (D96; the old R5 rule).
"""

from dataclasses import replace

from .. import presented

MAX_PICKS = 8  # the prompt asks for 5–8 (D96)
REASON_LENGTH = 100  # Plan.star_reason


def scope(line, among=None):
    ids = {plan.id for plan in line.plans}
    return ids if among is None else ids & {int(pid) for pid in among}


def cleared(line, ids):
    plans = [replace(plan, starred=False) if plan.starred and plan.id in ids else plan for plan in line.plans]
    return replace(line, plans=plans)


def candidates(line, ids):
    return [plan.id for plan in line.plans if plan.id in ids and plan.role != 'current']


def fit(line, ids):
    return min(MAX_PICKS, presented.room(cleared(line, ids)))


def choose(line, picks, ids):
    after = cleared(line, ids)
    allowed, room = set(candidates(line, ids)), presented.room(after)
    chosen, left = [], []
    for plan_id, why in picks:
        taken = [pid for pid, _why in chosen]
        if plan_id not in allowed or plan_id in taken or plan_id in left:
            continue
        if len(chosen) >= MAX_PICKS:
            break
        if presented.added(after, [*taken, plan_id]) > room:
            left.append(plan_id)
            continue
        chosen.append((plan_id, why))
    return chosen, left


def reason(text):
    words = ' '.join(str(text or '').split())
    if len(words) <= REASON_LENGTH:
        return words
    return words[: REASON_LENGTH - 1].rsplit(' ', 1)[0].rstrip(' ,;:.—-') + '…'


def picks_from(answer):
    """[(plan id, reason)] from Claude's {'shortlist': [{plan_id, reason}]}; an entry that names no whole number is
    dropped."""
    out = []
    entries = answer.get('shortlist') if isinstance(answer, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        plan_id = entry.get('plan_id')
        if isinstance(plan_id, str) and plan_id.strip().isdigit():
            plan_id = int(plan_id)
        if isinstance(plan_id, bool) or not isinstance(plan_id, int):
            continue
        out.append((plan_id, reason(entry.get('reason'))))
    return out


def curated(line):
    if any(plan.starred for plan in line.plans):
        return 'starred plans'
    if any(plan.sold for plan in line.plans):
        return 'a sold plan'
    if any(plan.recommended for plan in line.plans):
        return 'a recommended plan'
    return ''
