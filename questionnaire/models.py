from django.conf import settings
from django.db import models

from deals.models import Deal

USER = settings.AUTH_USER_MODEL


class Questionnaire(models.Model):
    """One carrier form on one deal (plan.md §6.8; G8, G.6): created on the first write (never by a GET) and never
    deleted. Each slot's status is worked out on read (`questionnaire/values.py`).

    - `answers` / `sources`: {slot: value} and {slot: entry}, a slot being `field` or `block.<row id>.field`, written
      only through `deals.values.apply` (§3.7). Origins: typed, relay, client, ai, prefill (a frozen prefill: one a
      person confirmed or the officer's signature froze; G27).
    - `rows`: {block: [{id, origin, by, plan?, link?, doc?, key?}]}; list order is the row number, `plan` ties a row to
      the current plan it was started for (G134). Row ids come from `last_row_id` and are never reused (G43).
    - `client`: {slot: entry} the client's answers waiting for review (O.3.1, slices 53–54).
    - `cleared`: slots a person emptied on purpose; they hide the live prefill only (G33).
    - The officer's signature locks the form (`locked`; G52). `reopens` keeps {at, by, reason} per reopen (G54, OQ55).
    - `signed_document` and `signed_copies`: the copy filed at the officer's signature (G135, slice 43).
    - `flags`: open warnings, a stored count (O.3.7), rewritten by every write.
    """

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='questionnaires')
    form = models.CharField(max_length=40)
    form_version = models.CharField(max_length=20)
    answers = models.JSONField(default=dict, blank=True)
    sources = models.JSONField(default=dict, blank=True)
    rows = models.JSONField(default=dict, blank=True)
    client = models.JSONField(default=dict, blank=True)
    cleared = models.JSONField(default=list, blank=True)
    last_row_id = models.PositiveIntegerField(default=0)
    officer_name = models.CharField(max_length=200, blank=True)
    officer_signed_at = models.DateTimeField(null=True, blank=True)
    officer_signed_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    officer_link = models.PositiveBigIntegerField(null=True, blank=True)  # review sits to the right: a plain id
    officer_authorized = models.BooleanField(default=False)
    agent_name = models.CharField(max_length=200, blank=True)
    agent_signed_at = models.DateTimeField(null=True, blank=True)
    agent_signed_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    signed_document = models.ForeignKey(
        'documents.Document', null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    signed_copies = models.JSONField(default=list, blank=True)
    reopens = models.JSONField(default=list, blank=True)
    flags = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['deal', 'form'], name='questionnaire_one_per_deal_form')]

    def __str__(self):
        return f'{self.form} on deal {self.deal_id}'

    @property
    def locked(self):
        return self.officer_signed_at is not None
