from django.conf import settings
from django.db import models
from django.db.models import Q

from deals.models import Deal


class Plan(models.Model):
    ROLES = [('current', 'Current'), ('renewal', 'Renewal'), ('alternate', 'Alternate')]

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='plans')
    line = models.CharField(max_length=20)
    role = models.CharField(max_length=10, choices=ROLES)
    carrier = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    plan_number = models.CharField(max_length=100, blank=True)
    renews = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='renewal_set')
    # Alternates only: the current plans it takes the place of — none, one or several (§5.4).
    replaces = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='replaced_by')
    values = models.JSONField(default=dict, blank=True)
    sources = models.JSONField(default=dict, blank=True)
    enrollment = models.JSONField(default=dict, blank=True)
    enrollment_on = models.BooleanField(default=False)
    census_names = models.JSONField(default=list, blank=True)
    starred = models.BooleanField(default=False)
    recommended = models.BooleanField(default=False)
    sold = models.BooleanField(default=False)
    sold_at = models.DateTimeField(null=True, blank=True)
    option_label = models.CharField(max_length=10, blank=True)
    source_document = models.ForeignKey(
        'documents.Document', null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['deal', 'line', 'role', 'sort_order'])]
        constraints = [
            models.UniqueConstraint(
                fields=['renews'], condition=Q(renews__isnull=False), name='one_renewal_per_current_plan'
            ),
            models.UniqueConstraint(
                fields=['deal', 'option_label'], condition=~Q(option_label=''), name='option_label_unique_per_deal'
            ),
        ]
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.carrier} {self.name}'


class Package(models.Model):
    """A set of plans the member builds on one line (§5.5). Totals are computed on read, never stored."""

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='packages')
    line = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    plans = models.ManyToManyField(Plan, related_name='packages', blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['deal', 'line', 'name'], name='package_name_unique_per_line')]
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name
