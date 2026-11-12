"""Jobs and the deal's AI settings (plan.md §6.4; O.3.3, D.6). `ai` holds no business data: plans, answers and people
stay with their owners, which apply a job's changes through their own services.

Chat, ChatMessage and CarrierNote join in slice 24; firm-level jobs with no deal wait with the ledger (OQ6).
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from deals.models import Activity, Deal

from . import kinds

USER = settings.AUTH_USER_MODEL


class Job(models.Model):
    """One read, chat turn, re-check, rank, locate or issue. Started by `services.jobs.start`, run by the worker
    (`manage.py run_worker`), which claims the oldest queued job whose deal and lane are free; one job runs per deal
    and lane at a time (the constraint below). `steps` are short lines for the progress card, never file text or
    names; `result` holds what the job found (a change set from slice 18; a locate's counts)."""

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='ai_jobs')
    lane = models.CharField(max_length=10, choices=[(lane, lane) for lane in kinds.LANES])
    kind = models.CharField(max_length=12, choices=[(kind, kind) for kind in kinds.KINDS])
    target = models.CharField(max_length=30, blank=True)
    documents = models.JSONField(default=list, blank=True)  # document ids, in the order they are read
    params = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=10, choices=[(status, status) for status in kinds.STATUSES], default=kinds.QUEUED
    )
    progress = models.PositiveSmallIntegerField(default=0)  # 0–100
    steps = models.JSONField(default=list, blank=True)
    result = models.JSONField(default=dict, blank=True)
    land = models.CharField(max_length=10, blank=True)  # how a read lands (D71; slice 18)
    wait_reason = models.CharField(max_length=200, blank=True)
    resolution = models.CharField(max_length=20, blank=True)  # stopped, reaped; applied, discarded, undone (18–20)
    activity = models.ForeignKey(Activity, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    model = models.CharField(max_length=60, blank=True)
    usage = models.JSONField(default=dict, blank=True)
    cost_usd = models.DecimalField(max_digits=9, decimal_places=4, default=0)
    error = models.CharField(max_length=300, blank=True)  # a sentence for the person; never file text or names
    cancel_requested_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    actor_label = models.CharField(max_length=100, blank=True)  # who started it when no user did (the portal)
    worker = models.CharField(max_length=100, blank=True)  # the worker that claimed it (host:pid)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)  # beats on progress, never on a timer (D105)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['deal', 'lane'], condition=Q(status=kinds.RUNNING), name='one_running_job_per_deal_and_lane'
            ),
        ]
        indexes = [models.Index(fields=['status', 'created_at']), models.Index(fields=['deal', 'created_at'])]
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.kind} job {self.id} ({self.status})'


class DealAi(models.Model):
    """The deal's AI settings (D100, D104): the table lock, its budget and the next chat number. Created on the first
    write (slice 24's lock and budget); reads of a deal without one get the defaults, so a GET never writes."""

    deal = models.OneToOneField(Deal, on_delete=models.CASCADE, related_name='ai')
    locked_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    locked_at = models.DateTimeField(null=True, blank=True)
    budget_usd = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)  # null: the setting
    next_chat = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'AI settings of deal {self.deal_id}'
