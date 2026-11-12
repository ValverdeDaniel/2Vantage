from django.conf import settings
from django.db import models
from django.db.models import Q

from deals.models import Deal

from . import flags as open_flags


class LivePlans(models.Manager):
    """The default manager hides removed plans (§6.7, O.3.7; F60), so every read, related managers included
    (`deal.plans`, `package.plans`, `plan.replaces`), sees live plans only. `Plan.all_objects` serves links and
    history: Revert's restore, and telling a removed plan from one that was never on the deal."""

    def get_queryset(self):
        return super().get_queryset().filter(removed_at__isnull=True)


class Plan(models.Model):
    """One plan on a deal's line (plan.md §5.4, §6.7). Roles and links change only through `services.roles`, marks
    through `services.marks`, order through `services.ordering`; PATCH takes only the plan's own text and values."""

    ROLES = [('current', 'Current'), ('renewal', 'Renewal'), ('alternate', 'Alternate')]

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='plans')
    line = models.CharField(max_length=20)
    role = models.CharField(max_length=10, choices=ROLES)
    carrier = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    plan_number = models.CharField(max_length=100, blank=True)
    # The name on client documents (J14); prints in client files in place of the plan name (slice 25).
    client_name = models.CharField(max_length=200, blank=True)
    renews = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='renewal_set')
    # Alternates only: the current plans it takes the place of — none, one or several (§5.4).
    replaces = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='replaced_by')
    values = models.JSONField(default=dict, blank=True)
    sources = models.JSONField(default=dict, blank=True)
    # The plan's codes, part of its identity for re-reads and SBCs (F143; slice 18).
    codes = models.JSONField(default=list, blank=True)
    # The reader's match reference (D.6's `Plan.read`); never copied (O.6 #9; slice 18).
    read_ref = models.JSONField(default=dict, blank=True)
    enrollment = models.JSONField(default=dict, blank=True)
    enrollment_on = models.BooleanField(default=False)
    census_names = models.JSONField(default=list, blank=True)
    # ★ = on the proposal, at most 16 columns a line through `presented.room()` (F50, F119).
    starred = models.BooleanField(default=False)
    star_reason = models.CharField(max_length=100, blank=True)  # "Hand-picked" or Rank's; never on client files
    starred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    starred_at = models.DateTimeField(null=True, blank=True)
    recommended = models.BooleanField(default=False)
    sold = models.BooleanField(default=False)
    sold_at = models.DateTimeField(null=True, blank=True)
    option_label = models.CharField(max_length=10, blank=True)  # goes with option numbers (slice 25)
    # A priced version and how it was made (F76–F84; slice 35).
    derived_from = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='versions')
    derived = models.JSONField(default=dict, blank=True)
    # Whether the carrier's quoted rates already include the bundling discount (F78; the old `bundling_state`): a
    # bundled version of an `included` quote would discount it twice, so it is refused.
    BUNDLING = [('', 'Not confirmed'), ('unbundled', 'Confirmed unbundled'), ('included', 'Rates already include it')]
    bundling = models.CharField(max_length=10, choices=BUNDLING, blank=True, default='')
    flags = models.PositiveIntegerField(default=0)  # open warnings, a stored count (O.3.7; slice 17)
    source_document = models.ForeignKey(
        'documents.Document', null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    notes = models.TextField(blank=True)
    # One sequence per line, read only through `order.layout` (F43, F120, OQ13).
    sort_order = models.PositiveIntegerField(default=0)
    removed_at = models.DateTimeField(null=True, blank=True)  # soft delete, undone by Revert (F60)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = LivePlans()  # first, so it is the default manager
    all_objects = models.Manager()  # noqa: DJ012 (ruff reads a second manager as a field)

    class Meta:
        indexes = [models.Index(fields=['deal', 'line', 'role', 'sort_order'])]
        constraints = [
            models.UniqueConstraint(
                fields=['renews'],
                condition=Q(renews__isnull=False, removed_at__isnull=True),
                name='one_renewal_per_current_plan',
            ),
            models.UniqueConstraint(
                fields=['deal', 'option_label'], condition=~Q(option_label=''), name='option_label_unique_per_deal'
            ),
        ]
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.carrier} {self.name}'

    def save(self, *args, **kwargs):
        """Every save of the values or sources rewrites `flags`, the stored count of open warnings, in the same
        transaction (O.3.7, Q.3 #9; quotes/flags.py). Writes that `bulk_update` stamp it themselves."""
        written = kwargs.get('update_fields')
        if written is None or {'values', 'sources', 'line'} & set(written):
            if open_flags.stamp(self) and written is not None:
                kwargs['update_fields'] = [*written, 'flags']
        super().save(*args, **kwargs)


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


class SavedView(models.Model):
    """A saved board setup, Mine and Shared (plan.md §6.7; F28, F29, OQ7; the old AdvisorFilterSet): the board's whole
    config, named, offered on one line or any line ('' = any). Not attached to a deal: the point is reuse across deals.
    Private to its owner until `shared`; anyone may use a shared one, only its owner or an admin changes it, and
    another person's private setup does not exist for anyone else (404). `config` is written only through
    `board.clean_config` for its `view`; the stop-loss board's setups (F29; slice 36) use the same row."""

    QUOTES = 'quotes'
    STOP_LOSS = 'stop-loss'
    VIEWS = [(QUOTES, 'Quote comparison'), (STOP_LOSS, 'Stop-loss analysis')]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='saved_views'
    )
    shared = models.BooleanField(default=False)
    view = models.CharField(max_length=20, choices=VIEWS, default=QUOTES)
    line = models.CharField(max_length=20, blank=True)  # '' = any line
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=200, blank=True)
    config = models.JSONField(default=dict, blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner', 'view', 'name'], name='saved_view_name_unique_per_owner'),
        ]
        ordering = ['sort_order', 'name', 'id']

    def __str__(self):
        return f'{self.name} ({self.view})'
