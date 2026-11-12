from django.db import models

from deals.models import Deal


class RfpRequest(models.Model):
    """One per deal, created by rfp's own services on their first write, never by a GET (plan.md §6.10; K.6). It
    replaces v1.1's `RfpConfig`. There is no line list: the lines asked for are the deal's requested lines (K16).

    - `route`: '' follows the band until the first send pins it, else 'warner' or 'direct' (§4; K20, K64).
    - `carriers`: carrier keys (`deals.carriers`), in registry order; `other_carriers`: "Also please quote", free text.
    - `funding`: a list of funding keys, or null for the default; `[]` is a real pick (K.5 #4).
    - `form`: '' (the Simplified form), 'small_group' or 'large_group'.
    - `include`: {file key: bool}, only the differences from the default (one key space, K.6).
    - `done`: {card: {by, at}} for coverage, request, checklist, packet and emails.
    - `sends`: {draft key: {on: 'YYYY-MM-DD', at: iso, by: user id, route, asked: [{key or null, name, lines}]}}, the
      frozen record of who was asked (N.3): Markets checked reads it through `selectors.asked_by_line`.
    Vocabularies stay out of the migration (rule 1): the services check them (slices 44–46)."""

    deal = models.OneToOneField(Deal, on_delete=models.CASCADE, primary_key=True, related_name='rfp_request')
    route = models.CharField(max_length=10, blank=True)
    carriers = models.JSONField(default=list, blank=True)
    other_carriers = models.CharField(max_length=300, blank=True)
    funding = models.JSONField(null=True, blank=True)
    form = models.CharField(max_length=20, blank=True)
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)  # ≤ 2,000, checked by the service
    include = models.JSONField(default=dict, blank=True)
    done = models.JSONField(default=dict, blank=True)
    sends = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'RFP for {self.deal}'
