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


class ProposalIssue(models.Model):
    """One issued version of a deal's proposal (plan.md §6.11; J102, J103, J.6.2, J.6.4; slice 32): v1, v2… per deal,
    never reused. Issue (`issues.start`) creates it `building` under the Deal lock, after quotes stamped the option
    numbers; the `issue` job builds the PDF, the PowerPoint and the workbook outside any lock, then stores them as
    protected Documents of kind `proposal` and marks it `issued` (`issues.finish`). A failed build marks it `failed`
    with a sentence, and Retry builds the same version again. Issued files are immutable, a record of what the client
    was sent: never rebuilt, never removed (the files' `protected` flag; RESTRICT here, so only the whole deal's
    deletion takes them). Not version history: no snapshot of deal data, no diff, no restore (§15)."""

    BUILDING, ISSUED, FAILED = 'building', 'issued', 'failed'
    STATES = [(BUILDING, 'Building'), (ISSUED, 'Issued'), (FAILED, 'Failed')]

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='proposal_issues')
    version = models.PositiveIntegerField()
    state = models.CharField(max_length=10, choices=STATES, default=BUILDING)
    pdf = models.ForeignKey('documents.Document', null=True, blank=True, on_delete=models.RESTRICT, related_name='+')
    pptx = models.ForeignKey('documents.Document', null=True, blank=True, on_delete=models.RESTRICT, related_name='+')
    xlsx = models.ForeignKey('documents.Document', null=True, blank=True, on_delete=models.RESTRICT, related_name='+')
    job = models.ForeignKey('ai.Job', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    error = models.CharField(max_length=300, blank=True)  # a failed build's sentence; never file text or a name
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['deal', 'version'], name='proposal_issue_version_per_deal')]
        ordering = ['-version']

    def __str__(self):
        return f'Proposal v{self.version} of deal {self.deal_id} ({self.state})'


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


class CoverImage(models.Model):
    """A picture the firm uploaded for its proposals (plan.md §6.11; J32, J33, J35; old `AgencyCoverImage` at
    891f1b3): firm-wide, picked per proposal as the cover's picture (`output.cover.image`) or any dark page's
    (`output.pictures.<place>` = "upload:<id>"). The stored `image` is the re-encode (`documents.images.reencode`: a
    JPEG, no metadata, long side ≤ STORE_SIDE), never the upload, and `thumb` its ≤ THUMB_SIDE copy for the builder's
    tiles. Neither file name says anything about the picture. A client file embeds its pixels, never its path or id."""

    MAX_IMAGES = 24
    MAX_BYTES = 10 * 1024 * 1024
    MAX_SIDE = 6000
    STORE_SIDE = 2400
    THUMB_SIDE = 600
    MAX_LABEL = 80

    image = models.FileField(upload_to='proposals/covers/')
    thumb = models.FileField(upload_to='proposals/covers/')
    label = models.CharField(max_length=MAX_LABEL, blank=True, default='')
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return self.label or f'Cover image {self.pk}'


class ProposalTemplate(models.Model):
    """A saved part of a proposal, Mine and Shared (plan.md §6.11; J68, OQ7; old `ProposalTemplate` at 891f1b3, cut
    to three kinds): how the documents look (`layout`), a line's rows and card stats (`rows`) or the executive summary
    (`summary`). `config` is {path: value}, each path cleaned by `config.clean` (a `rows` template's paths are relative
    to the line it is applied on). Applying one writes the deal's config through `set_config`; it never binds the deal,
    so a template edited later changes no proposal. Private until `shared`; anyone may use a shared one, only its
    owner or an admin changes it. The built-in layout lives in code (`template_store.BUILT_IN`)."""

    LAYOUT, ROWS, SUMMARY = 'layout', 'rows', 'summary'
    KINDS = [(LAYOUT, 'Document layout'), (ROWS, 'Row set'), (SUMMARY, 'Executive summary')]

    name = models.CharField(max_length=80)
    description = models.CharField(max_length=200, blank=True, default='')
    kind = models.CharField(max_length=10, choices=KINDS)
    line = models.CharField(max_length=20, blank=True, default='')  # '' = any line
    config = models.JSONField(default=dict, blank=True)
    shared = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='proposal_templates'
    )
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner', 'kind', 'name'], name='proposal_template_name_per_owner'),
        ]
        ordering = ['sort_order', 'name', 'id']

    def __str__(self):
        return self.name
