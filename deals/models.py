from django.conf import settings
from django.db import models

from . import clock, lifecycle

USER = settings.AUTH_USER_MODEL


class Client(models.Model):
    """An employer group. Its status (`relationship`; screens say "Status") is written only by
    `deals.services.set_status` and `sale_changed`, through the table in `deals/lifecycle.py` (§5.1)."""

    name = models.CharField(max_length=200, db_index=True)
    relationship = models.CharField(max_length=20, choices=lifecycle.STATUSES, default=lifecycle.PROSPECT)
    # The agency date it became a client (the sale's or the conversion's); cleared on a return to Prospect.
    client_since = models.DateField(null=True, blank=True)
    # True when a sale made it a client: un-selling undoes only this kind of conversion (CL3).
    converted_by_sale = models.BooleanField(default=False)
    owner = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(USER, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Deal(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='deals')
    effective_date = models.DateField(null=True, blank=True)
    stage = models.CharField(max_length=10, default='intake')
    lost_reason = models.CharField(max_length=300, blank=True)
    lost_at = models.DateTimeField(null=True, blank=True)
    lost_from_stage = models.CharField(max_length=10, blank=True)
    requested_lines = models.JSONField(default=list, blank=True)
    # The client's status when the deal opened. It follows status changes while no plan on the deal is sold, then
    # freezes; `rules.deal_type` reads it (Renewal only for existing_client; M14, CL8).
    opened_as = models.CharField(max_length=20, choices=lifecycle.STATUSES, default=lifecycle.PROSPECT)
    owner = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_by = models.ForeignKey(USER, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['client', 'effective_date'])]

    def __str__(self):
        return f'{self.client.name} ({self.effective_date or "no date"})'


class Activity(models.Model):
    """Who changed what, when (§3.7, O.3.2). Written only by `deals.activity`.

    `changes` holds before and after per key and target: [{"t": "plan:41", "k": {"rate_ee": ["612.50", "640"]}}];
    a key-only row keeps the keys alone ({"t": "member:7", "k": ["dob"]}). Summaries and changes never carry
    census values, person names or file names; a row about a file carries its `document_id`.
    """

    ACTOR_KINDS = [('user', 'User'), ('client', 'Client'), ('claude', 'Claude'), ('system', 'System')]

    deal = models.ForeignKey(Deal, null=True, blank=True, on_delete=models.CASCADE, related_name='activity')
    subject = models.CharField(max_length=100, blank=True)  # what a firm row (no deal) is about, e.g. "statement:5"
    area = models.CharField(max_length=20)
    action = models.CharField(max_length=20)
    actor = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    actor_kind = models.CharField(max_length=10, choices=ACTOR_KINDS, default='user')
    summary = models.CharField(max_length=300)
    changes = models.JSONField(default=list, blank=True)
    # True while `changes` holds before and after for at least one key and no key-only entry (kept on merge).
    revertible = models.BooleanField(default=False)
    # The file a row is about, as an id: deals sits left of documents in the chain (O.1), so no foreign key.
    document_id = models.PositiveBigIntegerField(null=True, blank=True)
    # What consecutive writes must share to be merged into this row (e.g. "quotes:values"); blank = never merged.
    coalesce_key = models.CharField(max_length=60, blank=True)
    count = models.PositiveIntegerField(default=1)
    reverts = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    reverted_at = models.DateTimeField(null=True, blank=True)
    reverted_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(default=clock.now)
    updated_at = models.DateTimeField(default=clock.now)

    class Meta:
        indexes = [models.Index(fields=['deal', 'created_at']), models.Index(fields=['area', 'created_at'])]
        ordering = ['-updated_at', '-id']

    def __str__(self):
        return self.summary


class AgencySettings(models.Model):
    """Single row, pk = 1, edited in Django admin (§6.2, §7.2)."""

    name = models.CharField(max_length=200, default='Vantage Risk Solutions')
    address = models.CharField(max_length=300, blank=True)
    city_state_zip = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    brand_color = models.CharField(max_length=7, default='#173a63')
    logo = models.FileField(upload_to='agency/', blank=True)
    default_commission = models.JSONField(default=dict, blank=True)
    rfp_return_email = models.EmailField(blank=True)
    # The agency producer, printed when a deal has no owner (and, from slice 38, no agent of record): rules.agent_name.
    producer_name = models.CharField(max_length=200, blank=True)
    producer_npn = models.CharField('producer NPN', max_length=20, blank=True)

    class Meta:
        verbose_name = 'agency settings'
        verbose_name_plural = 'agency settings'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """The stored row, else the defaults unsaved: a read never creates it (§3.6). Django admin adds it."""
        return cls.objects.filter(pk=1).first() or cls(pk=1)
