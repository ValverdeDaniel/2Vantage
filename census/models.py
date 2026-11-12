"""The census (plan.md §6.6; C.5, L.6, O.2, O.6 #13, #23).

A `Member` is one person: values in JSON with a parallel `sources` dict written only by `deals.values.apply()`
(§3.7), and a client's answers waiting in `client` until a person approves them. People are never deleted: removal is
soft (`removed_at`), a re-import restores them by identity, and `Member.objects` hides removed people and people a
client added who are still pending (O.6 #13); `all_objects` serves history and matching. A `CensusImport` keeps a
file's mapping and reformat recipe, never a sample value (§5.3.2). `CensusFacts` holds the counts other apps read,
rewritten by every census write in its transaction, and must equal a rebuild (O.3.7, OQ9 c; `manage.py
rebuild_facts`).
"""

from django.conf import settings
from django.db import models

from deals.models import Deal
from documents.models import Document

USER = settings.AUTH_USER_MODEL
PERSON = '*'  # the `client` slot of a whole person a client added (L.6): {status: pending|approved|rejected, link, at}


class LiveMembers(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(removed_at__isnull=True)
            .exclude(added_by_link__isnull=False, client__contains={PERSON: {'status': 'pending'}})
        )


class Member(models.Model):
    """One person on a deal's census (§6.6). Vocabularies stay out of the migration (rule 1): `census.fields`."""

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='members')
    kind = models.CharField(max_length=10)  # fields.EMPLOYEE or fields.DEPENDENT
    employee = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='dependents')
    position = models.PositiveIntegerField(default=0)  # file order
    values = models.JSONField(default=dict, blank=True)  # {census key: text} (§4.4, §5.3.1)
    sources = models.JSONField(default=dict, blank=True)  # {census key: source entry} (O.3.1); never `line`
    client = models.JSONField(default=dict, blank=True)  # client answers waiting for review, each with `prior` (L.6)
    added_by_link = models.PositiveBigIntegerField(null=True, blank=True)  # a plain id: review sits to the right
    removed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = LiveMembers()  # first, so it is the default manager: `deal.members` lists live people only
    all_objects = models.Manager()  # noqa: DJ012 (ruff reads a second manager as a field)

    class Meta:
        default_manager_name = 'objects'
        ordering = ['position', 'id']
        indexes = [models.Index(fields=['deal', 'removed_at'])]

    def __str__(self):
        return f'{self.kind} {self.id} on deal {self.deal_id}'  # never a name (§3.8)


class CensusImport(models.Model):
    """One census file being mapped, then applied or discarded (§5.3.2). No sample values (they are read from the
    file for each answer); `pivot` is the reformat's recipe only, the rows rebuilt from the file (C13)."""

    PROPOSED, APPLIED, DISCARDED = 'proposed', 'applied', 'discarded'
    STATUSES = [(PROPOSED, 'Proposed'), (APPLIED, 'Applied'), (DISCARDED, 'Discarded')]

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='census_imports')
    document = models.ForeignKey(Document, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    sheet_name = models.CharField(max_length=100, blank=True)
    header_row = models.PositiveIntegerField(default=1)  # 1-based
    first_data_row = models.PositiveIntegerField(default=2)  # 1-based
    headers = models.JSONField(default=list, blank=True)
    mapping = models.JSONField(default=list, blank=True)  # [{column, header, field, confidence, low}]
    pivot = models.JSONField(default=dict, blank=True)  # census.pivot.STORED keys; {} = not one row per benefit
    status = models.CharField(max_length=10, default=PROPOSED)  # STATUSES; kept out of the migration (rule 1)
    stats = models.JSONField(default=dict, blank=True)  # {rows, employees, dependents, created, updated, removed, kept}
    created_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    # `job` (the read that proposed it, an ai.Job) arrives with Claude's census reader, slice 51.

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'Census import {self.id} ({self.status})'


class CensusSettings(models.Model):
    """One per deal, created on the first write (`set_rules`, slice 57): the per-deal Auto, Required or Waived of each
    column; Waived beats every other reason (OQ17, C27). COBRA lives in `Intake.checklist` (O.6 #2)."""

    deal = models.OneToOneField(Deal, on_delete=models.CASCADE, primary_key=True, related_name='census_settings')
    rules = models.JSONField(default=dict, blank=True)  # {census key: 'required' | 'waived'}; absent = auto
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Census settings for deal {self.deal_id}'


class CensusFacts(models.Model):
    """The census counts other apps read (§5.3.5, §6.6; N.1, I.6, L.6), one row per deal with a census. A stored
    count, the exception to "computed on read": census's services rewrite it in the write's transaction, and it must
    equal `census.facts.compute` (Q.3 #9)."""

    deal = models.OneToOneField(Deal, on_delete=models.CASCADE, primary_key=True, related_name='census_facts')
    employees = models.PositiveIntegerField(default=0)
    dependents = models.PositiveIntegerField(default=0)
    errors = models.PositiveIntegerField(default=0)
    warnings = models.PositiveIntegerField(default=0)
    required_total = models.PositiveIntegerField(default=0)
    required_filled = models.PositiveIntegerField(default=0)
    missing = models.JSONField(default=dict, blank=True)  # required blanks by column {key: count}
    pending_answers = models.PositiveIntegerField(default=0)  # client answers waiting (L.6; slice 53)
    pending_people = models.PositiveIntegerField(default=0)  # people a client added, waiting (L.6; slice 53)
    rollup = models.JSONField(default=dict, blank=True)  # census.rollup.compute
    last_import_at = models.DateTimeField(null=True, blank=True)  # F91 compares typed counts against it
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Census facts for deal {self.deal_id}'
