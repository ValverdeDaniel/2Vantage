from django.conf import settings
from django.db import models

from deals.models import Deal


class ProposalConfig(models.Model):
    """One per deal, created on the first write; a GET reads the defaults (plan.md §6.11; J.6.2, J.5 B27).

    `config` holds what the client files print, by path (`proposals.config`: title, intro, recommendation, reasons,
    order, lines, summary, markets, next_steps, experience, team, output), written only by `services.set_config`,
    merged by path under this row's lock. It never holds membership: `quotes.presented()` decides what prints (F119).
    `marks` are the builder's completed cards ({card: {by, at}, lines: {line: {card: {by, at}}}}; J18), workflow
    bookkeeping kept apart from what prints, written only by `services.set_mark` and `clear_marks`."""

    deal = models.OneToOneField(Deal, on_delete=models.CASCADE, primary_key=True, related_name='proposal_config')
    config = models.JSONField(default=dict, blank=True)
    marks = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Proposal for {self.deal}'
