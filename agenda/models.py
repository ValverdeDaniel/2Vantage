"""Agenda's two stored things (plan.md §6.13; I.6): a person's mark on a derived step, and a task added by hand.

Everything else the Agenda shows — the steps, the next step, the journey, progress, the sections — is worked out on
read from every app's facts (`agenda.steps`, `agenda.rows`) and never stored. Vocabularies (the mark kinds) stay out of
the migration (rule 1): `agenda.rules` holds them and the services check them.
"""

from django.conf import settings
from django.db import models

from deals import clock
from deals.models import Deal

USER = settings.AUTH_USER_MODEL


class StepMark(models.Model):
    """A person's decision about one of a deal's derived steps (I16–I26), firm-wide (OQ92): Later (`until` a day; the
    step is held back for everyone until then) or Done anyway (the step's signature `sig` as the server saw it, so the
    mark lapses by itself when the step's state, words or items change). One row per step (I23): setting one kind
    replaces the other. A lapsed row is ignored on read and replaced by the next mark, so nothing grows (I26)."""

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='step_marks')
    step_key = models.CharField(max_length=80)
    kind = models.CharField(max_length=10)  # rules.LATER | rules.DONE
    until = models.DateField(null=True, blank=True)
    sig = models.CharField(max_length=40, blank=True)
    note = models.TextField(blank=True)  # up to rules.MARK_NOTE_MAX; never in Activity
    by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    at = models.DateTimeField(default=clock.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['deal', 'step_key'], name='agenda_one_mark_per_step')]

    def __str__(self):
        return f'{self.kind} mark on {self.step_key}'


class LiveTasks(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Task(models.Model):
    """A task someone added to a deal by hand (I27–I34): never the client's, so it follows the deal. Done when
    `done_at` is set. A delete is soft (`deleted_at`, I33) and its Activity row's Revert brings it back."""

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=300)  # never in Activity
    due = models.DateField()
    note = models.TextField(blank=True)  # up to rules.TASK_NOTE_MAX; never in Activity
    assigned_to = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    done_at = models.DateTimeField(null=True, blank=True)
    done_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(default=clock.now)
    updated_at = models.DateTimeField(default=clock.now)

    objects = LiveTasks()  # hides deleted tasks
    all_objects = models.Manager()  # noqa: DJ012 (ruff reads a second manager as a field); Revert

    class Meta:
        ordering = ['due', 'id']
        base_manager_name = 'all_objects'
        indexes = [models.Index(fields=['deal', 'done_at', 'due'])]

    def __str__(self):
        return f'Task {self.pk}'

    @property
    def done(self):
        return self.done_at is not None
