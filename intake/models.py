from django.conf import settings
from django.db import models

from deals.models import Deal

USER = settings.AUTH_USER_MODEL


class Intake(models.Model):
    """One per deal, created on the first write, never by a GET (plan.md §6.5; B.6, O.2). A deal with no row reads as
    empty. `answers` holds §4.5's questions and `client_guidance`, with a parallel `sources` dict written only by
    `deals.values.apply()` (§3.7). Nothing is prefilled when the row is created."""

    deal = models.OneToOneField(Deal, on_delete=models.CASCADE, primary_key=True, related_name='intake')
    answers = models.JSONField(default=dict, blank=True)
    sources = models.JSONField(default=dict, blank=True)
    client = models.JSONField(default=dict, blank=True)  # client answers waiting for review (O.3.1; slice 53)
    rules = models.JSONField(default=dict, blank=True)  # per-question Auto, Required or Waived (B37, OQ17; slice 57)
    checklist = models.JSONField(default=dict, blank=True)  # the marketing checklist, COBRA included (slice 40)
    # The confirmed coverage-and-intent decisions, kept readable: {"decisions": {line: {in_force, this_year,
    # rate_guarantee_through}}, "by": user id, "by_name": ..., "at": ISO time}. {} = never confirmed. "Confirmed"
    # means the decisions still equal today's (B20); `coverage.decisions` works them out.
    intent_confirmed = models.JSONField(default=dict, blank=True)
    bor_name = models.CharField(max_length=200, blank=True)
    bor_signed_at = models.DateTimeField(null=True, blank=True)
    bor_signed_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    marketed_at = models.DateTimeField(null=True, blank=True)
    marketed_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    flags = models.PositiveIntegerField(default=0)  # open warnings, a stored count (O.3.7; from slice 39)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Intake for deal {self.deal_id}'


class CurrentCoverage(models.Model):
    """One line of coverage the client has today, or a gap the deal proposes to fill (`in_force` false; §6.5, B14).

    The coverage subcards and the intent card edit these rows through one service (OQ15). The first row of a line
    is the one the intent card shows and decides on (the old app's rule: a line may hold two rows mid-transition).
    Once a line has current plans in the Advisor, carrier and funding come from the plans (`quotes.facts.incumbent`)
    and the row keeps its dates, `in_force` and notes."""

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='coverage')
    # Vocabularies stay out of migrations (rule 1): the services check line (§4.1), funding (§4.6) and the
    # commission source (`coverage.COMMISSION_SOURCES`).
    line = models.CharField(max_length=20)
    carrier = models.CharField(max_length=200, blank=True)
    funding = models.CharField(max_length=20, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    renewal_date = models.DateField(null=True, blank=True)
    rate_guarantee_through = models.DateField(null=True, blank=True)
    in_force = models.BooleanField(default=True)
    notes = models.CharField(max_length=300, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    on_proposal = models.BooleanField(default=True)
    commission = models.JSONField(default=dict, blank=True)  # a comp {type, value} (deals/comp.py); {} = unknown
    commission_source = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['sort_order', 'id']
        indexes = [models.Index(fields=['deal', 'line'])]

    def __str__(self):
        return f'{self.line}: {self.carrier or "—"}'
