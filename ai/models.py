"""Jobs and the deal's AI settings (plan.md §6.4; O.3.3, D.6). `ai` holds no business data: plans, answers and people
stay with their owners, which apply a job's changes through their own services.

Slice 24 adds the chats (`Chat`, `ChatMessage`; D7, D79), a turn's chat on its job, and the admins' carrier notes
(`CarrierNote`, D119). Firm-level jobs with no deal wait with the ledger (OQ6).
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
    chat = models.ForeignKey('Chat', null=True, blank=True, on_delete=models.SET_NULL, related_name='jobs')  # a turn's
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


class Call(models.Model):
    """One call to Claude, priced from the model that answered (plan.md §10.3; D8, D51, D53; slice 18). The ledger the
    total cap reads (`AI_TOTAL_BUDGET_USD`): a call is reserved at its worst-case estimate before it is sent, then
    settled at what it really used, so two calls at once can never pass the cap between them. A call keeps its row
    when its deal or job goes, so the total stays true. Never a file name, its text or a value: counts and money."""

    PENDING, DONE, FAILED, STOPPED = 'pending', 'done', 'failed', 'stopped'
    STATUSES = [(PENDING, 'Sent'), (DONE, 'Answered'), (FAILED, 'Failed'), (STOPPED, 'Stopped')]

    job = models.ForeignKey(Job, null=True, blank=True, on_delete=models.SET_NULL, related_name='calls')
    deal = models.ForeignKey(Deal, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    purpose = models.CharField(max_length=20)  # read, recheck, turn, rank; eval (the Eval lane, no deal)
    model = models.CharField(max_length=60)  # asked for; `answered` is who answered (and priced it)
    answered = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default=PENDING)
    estimate_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)  # input + max_tokens, before
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)  # what it used, after
    usage = models.JSONField(default=dict, blank=True)  # input, output, cache write and read tokens
    stop_reason = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['status'])]
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.purpose} call {self.id} ({self.status})'


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


class Chat(models.Model):
    """One conversation with Claude on a deal (D7): everyone on the deal sees every chat (OQ3). Numbered per deal
    under the DealAi lock (`next_chat`), on its first message, so an unsent "＋ New chat" leaves nothing behind."""

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='ai_chats')
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=80, blank=True)  # '' reads as "Chat N"
    tab = models.CharField(max_length=20, blank=True)  # the deal tab it started on
    created_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)  # a person last wrote in it
    last_used_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['deal', 'number'], name='one_chat_number_per_deal')]
        ordering = ['-last_used_at', '-id']

    def __str__(self):
        return f'Chat {self.number} of deal {self.deal_id}'


class ChatMessage(models.Model):
    """One message of a chat (D79): a person's words or Claude's reply, and the turn it belongs to. No context and no
    cost are kept here: the turn's job holds what it cost and what it changed."""

    USER_ROLE, ASSISTANT = 'user', 'assistant'
    ROLES = [(USER_ROLE, 'Person'), (ASSISTANT, 'Claude')]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLES)
    text = models.TextField()
    author = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    job = models.ForeignKey(Job, null=True, blank=True, on_delete=models.SET_NULL, related_name='messages')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.role} message {self.id}'


class CarrierNote(models.Model):
    """An admin's note about one carrier's files, added to every Claude call about that carrier, outside the cache
    (D119; the stand-in for lessons, OQ4). `carrier` is a key of `deals.carriers` (checked by the admin form)."""

    carrier = models.CharField(max_length=60, unique=True)
    text = models.TextField()
    updated_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['carrier']

    def __str__(self):
        return f'Note on {self.carrier}'
