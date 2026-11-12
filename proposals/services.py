"""Writes to the proposal configuration (plan.md §6.11, §7.12). Retires with `ProposalConfig`'s rebuild in slice 25.

`lines` no longer holds membership (F119): ★ is "on the proposal", so a line's list of plans to present is turned
into quotes' own doors. The plans that should print and are neither current nor only recommended get a star, the
others lose theirs (on a line with no stars, taking one plan off stars every other quote; J13); an empty list clears
the line's shortlist (F55); and when the presented alternates come back in another order, the plan that moved takes
one step with the order door (F43). Title, notes and reasons stay here.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, lines
from deals.values import locked
from quotes import presented
from quotes import selectors as quotes
from quotes import services as plans

from .models import ProposalConfig

MAX_REASON = 2000


def _ids(line, ids):
    if line not in lines.BY_KEY or not isinstance(ids, list):
        raise ValidationError({'lines': [f'"{line}" is not a line of coverage.']})
    try:
        return [int(pid) for pid in ids]
    except (TypeError, ValueError) as exc:
        raise ValidationError({'lines': ['Lines must map a line to plan ids.']}) from exc


def _present(user, deal, line, wanted):
    """Make the line present `wanted` (plan ids, in the order the person listed them) through quotes' doors."""
    state = quotes.line_state(deal, line)
    rows = {plan.id: plan for plan in state.plans}
    if set(wanted) - set(rows):
        raise ValidationError({'lines': [f"A plan is not on this deal's {lines.label(line)} line."]})
    if not wanted:
        plans.clear_shortlist(user, deal, line)
        return
    stars = {pid for pid in wanted if rows[pid].role != 'current' and (rows[pid].starred or not rows[pid].recommended)}
    starred = {pid for pid, plan in rows.items() if plan.starred}
    if starred - stars:
        plans.star(user, deal, sorted(starred - stars), False)
    if stars - starred:
        plans.star(user, deal, sorted(stars - starred), True)
    state = quotes.line_state(deal, line)
    shown = [plan.id for plan in presented.presented(state.data)]
    alternates = [pid for pid in shown if rows[pid].role == 'alternate']
    asked = [pid for pid in wanted if pid in alternates]
    if sorted(asked) == sorted(alternates) and asked != alternates:
        moved = next(pid for pid, was in zip(asked, alternates, strict=True) if pid != was)
        plans.arrange(user, deal, line, ('move', moved, -1, shown))


@transaction.atomic
def save_config(user, deal, data):
    if 'lines' in data:  # quotes' doors lock the Deal first, so they run before the config row is locked (§3.7)
        chosen = data['lines'] or {}
        if not isinstance(chosen, dict):
            raise ValidationError({'lines': ['Lines must map a line to plan ids.']})
        for line, ids in chosen.items():
            _present(user, deal, line, _ids(line, ids))
    ProposalConfig.for_deal(deal)
    config = locked(ProposalConfig, deal.pk)
    edited = False
    if 'title' in data:
        config.title = (data['title'] or '').strip()[:200]
        edited = True
    if 'notes' in data:
        config.notes = data['notes'] or ''
        edited = True
    if 'reasons' in data:
        reasons = data['reasons'] or {}
        if not isinstance(reasons, dict):
            raise ValidationError({'reasons': ['Reasons must map a line to text.']})
        for line, text in reasons.items():
            if line not in lines.BY_KEY:
                raise ValidationError({'reasons': [f'"{line}" is not a line of coverage.']})
            if len(text or '') > MAX_REASON:
                raise ValidationError({'reasons': [f'Keep the reasons under {MAX_REASON} characters.']})
        config.reasons = {**config.reasons, **{k: (v or '').strip() for k, v in reasons.items()}}
        edited = True
    if edited:
        config.updated_by = user
        config.save()
        activity.record(deal, user, 'proposal', 'updated', 'Edited', 1, 'proposal:config', 'proposal setting')
    return config
