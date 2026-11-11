from django.conf import settings
from django.db import models

from . import clock

USER = settings.AUTH_USER_MODEL


class Client(models.Model):
    RELATIONSHIPS = [('new', 'New'), ('existing', 'Existing')]

    name = models.CharField(max_length=200, db_index=True)
    relationship = models.CharField(max_length=10, choices=RELATIONSHIPS, default='new')
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
    owner = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_by = models.ForeignKey(USER, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['client', 'effective_date'])]

    def __str__(self):
        return f'{self.client.name} ({self.effective_date or "no date"})'


class Activity(models.Model):
    """Who changed what, when (§3.7). Summaries never contain census values or person names."""

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='activity')
    actor = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    actor_label = models.CharField(max_length=200, blank=True)
    area = models.CharField(max_length=20)
    action = models.CharField(max_length=20)
    summary = models.CharField(max_length=300)
    count = models.PositiveIntegerField(default=1)
    # What consecutive writes must share to be merged into this row (e.g. "quotes:values"); blank = never merged.
    coalesce_key = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(default=clock.now)
    updated_at = models.DateTimeField(default=clock.now)

    class Meta:
        indexes = [models.Index(fields=['deal', '-created_at'])]
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
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
