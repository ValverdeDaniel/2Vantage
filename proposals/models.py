from django.conf import settings
from django.db import models

from deals.models import Deal


class ProposalConfig(models.Model):
    """One per deal (plan.md §6.8). `lines` = {line: [plan ids in display order]}; empty = the defaults (§8.12)."""

    deal = models.OneToOneField(Deal, on_delete=models.CASCADE, primary_key=True, related_name='proposal_config')
    title = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    lines = models.JSONField(default=dict, blank=True)
    reasons = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Proposal for {self.deal}'

    @classmethod
    def for_deal(cls, deal):
        config, _ = cls.objects.get_or_create(deal=deal)
        return config
