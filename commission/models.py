"""Commission's rows (plan.md §6.9; H.6): who can hold a share, the firm defaults, a deal's agreed rates and split,
and a client's split. The booked records (`Record`) join with slice 49; the ledger waits (OQ6 is No).

Vocabularies stay out of migrations (rule 1): `kind`, a row's role and basis are checked by the services against
`commission/vocab.py`. A Comp is `{type, value}` with the exact decimal as text (`deals/comp.py`). A split row is
`{party, role, amount, renewal_amount, basis, expires_after_years, works_it}` (§5.6), `party` a Party id.
"""

from django.conf import settings
from django.db import models

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
