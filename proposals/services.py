"""Writes to the proposal configuration (plan.md §6.8, §7.9)."""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, lines
from deals.values import locked
from quotes.models import Plan

from .models import ProposalConfig

MAX_REASON = 2000


@transaction.atomic
def save_config(user, deal, data):
    ProposalConfig.for_deal(deal)
    config = locked(ProposalConfig, deal.pk)
    if 'title' in data:
        config.title = (data['title'] or '').strip()[:200]
    if 'notes' in data:
        config.notes = data['notes'] or ''
    if 'lines' in data:
        chosen = data['lines'] or {}
        if not isinstance(chosen, dict):
            raise ValidationError({'lines': ['Lines must map a line to plan ids.']})
        cleaned = {}
        for line, ids in chosen.items():
            if line not in lines.BY_KEY or not isinstance(ids, list):
                raise ValidationError({'lines': [f'"{line}" is not a line of coverage.']})
            ids = [int(pid) for pid in ids]
            known = set(Plan.objects.filter(deal=deal, line=line, id__in=ids).values_list('id', flat=True))
            if known != set(ids):
                raise ValidationError({'lines': [f"A plan is not on this deal's {lines.label(line)} line."]})
            cleaned[line] = ids
        config.lines = {**config.lines, **cleaned}
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
    config.updated_by = user
    config.save()
    activity.record(deal, user, 'proposal', 'updated', 'Edited', 1, 'proposal:config', 'proposal setting')
    return config
