from django.conf import settings
from django.db import models

from deals.models import Deal


class ProposalConfig(models.Model):
    """One per deal, created on the first write; a GET reads the defaults (plan.md §6.11; J.6.2, J.5 B27).

    `config` holds what the client files print, by path (`proposals.config`: title, intro, recommendation, reasons,
    order, lines, summary, markets, next_steps, experience, team, output), written only by `services.set_config`,
    merged by path under this row's lock. It never holds membership: `quotes.presented()` decides what prints (F119).
    `marks` are the builder's completed cards ({card: {by, at}, lines: {line: {card: {by, at}}}}; J18), workflow
    bookkeeping kept apart from what prints, written only by `services.set_mark` and `clear_marks`."""

    deal = models.OneToOneField(Deal, on_delete=models.CASCADE, primary_key=True, related_name='proposal_config')
    config = models.JSONField(default=dict, blank=True)
    marks = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Proposal for {self.deal}'


class FirmPages(models.Model):
    """The firm's own pages in the Presentation format (plan.md §6.11; J125, J138, J155): who the firm is in its own
    words and figures, and how it works with a client through the year. One row (pk 1), edited in Django admin until
    the Firm pages drawer (slice 34). Blank prints no page: nothing here is ever filled in for the firm (OQ41).

    `about_stats`: [{value, label, note}] (≤6); `service_calendar`: [{meeting, topics: [text], when}] (≤8)."""

    MAX_ABOUT = 900
    MAX_STATS = 6
    MAX_CALENDAR = 8

    about_text = models.TextField(blank=True, default='')
    about_stats = models.JSONField(default=list, blank=True)
    service_calendar = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'firm pages'
        verbose_name_plural = 'firm pages'

    def __str__(self):
        return 'Firm pages'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """The stored row, else the blank defaults unsaved: a read never creates it (§3.6)."""
        return cls.objects.filter(pk=1).first() or cls(pk=1)


class TeamMember(models.Model):
    """A person on the firm's team, for the team and bio pages (plan.md §6.11; J125, J138, J155). One record for both
    pages, so a title cannot read one way on the team page and another in a bio. The stored photo is a re-encoded
    JPEG with no metadata, never the upload; no client surface sees its path: the files embed its pixels."""

    MAX_MEMBERS = 40
    MAX_BIO = 1400

    name = models.CharField(max_length=120)
    title = models.CharField(max_length=120, blank=True, default='')
    # What they do for the client, the heading on their card ("Benefits advisor").
    group = models.CharField(max_length=80, blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    bio = models.TextField(blank=True, default='')
    photo = models.FileField(upload_to='proposals/team/', blank=True, default='')
    # On a proposal unless a deal picks its own team (`config.team`, slice 34).
    on_by_default = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name
