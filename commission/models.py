"""Commission's rows (plan.md §6.9; H.6): who can hold a share, the firm defaults, a deal's agreed rates and split,
a client's split, and the booked records (slice 49). The ledger waits (OQ6 is No).

Vocabularies stay out of migrations (rule 1): `kind`, a row's role and basis, a record's status are checked by the
services against `commission/vocab.py`. A Comp is `{type, value}` with the exact decimal as text (`deals/comp.py`). A
split row is `{party, role, amount, renewal_amount, basis, expires_after_years, works_it}` (§5.6), `party` a Party id.
"""

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from deals import clock
from deals.models import Client, Deal

from . import vocab

USER = settings.AUTH_USER_MODEL


class Party(models.Model):
    """Someone who can hold a share: a producer (with or without a login) or an outside partner. The house is
    implicit, never a row. A producer user's Party is created on their first split save (H95, H11); a GET never
    creates one. Written only by `commission.services`."""

    kind = models.CharField(max_length=10, default=vocab.PRODUCER)
    name = models.CharField(max_length=200)
    user = models.OneToOneField(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='commission_party')
    email = models.CharField(max_length=254, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    npn = models.CharField('NPN', max_length=20, blank=True)
    appointed = models.BooleanField(default=False)
    default_split = models.JSONField(null=True, blank=True)  # a Comp a pick fills in (H12)
    # The producer's share of agency revenue; null = the firm default (Settings). The house keeps the rest (H97).
    first_year_pct = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    renewal_pct = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'id']
        verbose_name_plural = 'parties'

    def __str__(self):
        return self.name


class Settings(models.Model):
    """The firm defaults (pk 1, H100): the producer's share of agency revenue in the first year and on renewals,
    when the primary has no figure of their own. A read never creates the row. The gap grace waits with the ledger
    (slice 50; OQ6 is No)."""

    first_year_pct = models.DecimalField(max_digits=7, decimal_places=4, default=vocab.DEFAULT_FIRST_YEAR_PCT)
    renewal_pct = models.DecimalField(max_digits=7, decimal_places=4, default=vocab.DEFAULT_RENEWAL_PCT)
    confirmed_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'commission settings'
        verbose_name_plural = 'commission settings'

    def __str__(self):
        return 'Commission settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """The stored row, else the defaults unsaved."""
        return cls.objects.filter(pk=1).first() or cls(pk=1)


class Commission(models.Model):
    """One per deal, created on the first write (O.2): the agreed rate per line with its `sources` entry (written
    only by `deals.values.apply`, H5), the deal's own split (`{rows}`, an override of the client's; H20) and the
    typed "year with us" (H30)."""

    deal = models.OneToOneField(Deal, primary_key=True, on_delete=models.CASCADE, related_name='commission')
    rates = models.JSONField(default=dict, blank=True)  # {line: Comp}
    sources = models.JSONField(default=dict, blank=True)  # {line: source entry}
    split = models.JSONField(null=True, blank=True)  # {'rows': [Row]} or null: the client's split applies
    year_number = models.PositiveSmallIntegerField(null=True, blank=True)
    updated_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Commission of deal {self.deal_id}'


class ClientSplit(models.Model):
    """The client's split, one per client (H20, H106): it applies to every deal of the client that has no split of
    its own."""

    client = models.OneToOneField(Client, primary_key=True, on_delete=models.CASCADE, related_name='commission_split')
    rows = models.JSONField(default=list, blank=True)
    updated_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Split of client {self.client_id}'


class Record(models.Model):
    """One booked line (H25–H37; §6.9): a deal's line and carrier frozen at the sale (OQ75: one record per carrier on a
    line), or a line booked by hand with no deal (Add to book, H58). Never deleted: un-selling voids it (H32), and the
    client and the deal are PROTECTed (H112). Written only by `commission.services` (booking, records).

    The sale's facts live in `values` (`premium_annual` at cents as text, `rate` a Comp, `employees`, `plan_label`,
    `plan_ids`, `policy_number`) and in four columns (`carrier`, `effective_date`, `term_end`, `status`), each with its
    `sources` entry (origin `sale`, `typed`, `in_force` or `agency`), all written through `deals.values.apply`: a
    booking refreshes the `sale` keys and never a `typed` one (H28). `terms` freezes who gets what, `{house_pct, rows,
    from, shares, reason}`; shares and dollars are worked out on read (H29), unless `shares` was typed (H55)."""

    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='commission_records')
    deal = models.ForeignKey(Deal, null=True, blank=True, on_delete=models.PROTECT, related_name='commission_records')
    line = models.CharField(max_length=20)
    carrier = models.CharField(max_length=200, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    term_end = models.DateField(null=True, blank=True)
    year_number = models.PositiveSmallIntegerField(null=True, blank=True)  # null = not known (renewal terms, H30)
    is_renewal = models.BooleanField(default=False)
    status = models.CharField(max_length=12, default=vocab.BOOKED)
    values = models.JSONField(default=dict, blank=True)
    sources = models.JSONField(default=dict, blank=True)
    terms = models.JSONField(default=dict, blank=True)
    party_ids = ArrayField(models.IntegerField(), default=list, blank=True)  # written with the terms (review 16)
    notes = models.TextField(blank=True)
    booked_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    booked_at = models.DateTimeField(default=clock.now)
    updated_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['deal', 'line', 'carrier'],
                condition=models.Q(deal__isnull=False),
                name='commission_record_one_per_deal_line_carrier',
            )
        ]
        indexes = [
            GinIndex(fields=['party_ids'], name='commission_record_parties'),
            models.Index(fields=['client', 'line'], name='commission_record_client_line'),
        ]

    def __str__(self):
        return f'Commission record {self.id}: {self.line} · {self.carrier or "—"}'
