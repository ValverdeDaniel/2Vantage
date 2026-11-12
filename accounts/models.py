from django.conf import settings
from django.db import models

# The commission tier (H101, H102, OQ73): none sees no ledger figures, own sees the records it is a party to, all sees
# every record. An admin is always all (accounts.access.commission_tier).
COMMISSION_TIERS = [('none', 'None'), ('own', 'Own'), ('all', 'All')]


class Profile(models.Model):
    """Per-person flags, edited in Django admin (plan.md §6.1; A3). A user with no row reads the defaults."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    # A "direct" person: Claude's quote reads land at once with Undo, Opus may be picked, and the deal's AI budget can
    # be overridden (D71, D91, D24).
    claude_direct = models.BooleanField(default=False)
    commissions_access = models.CharField(
        max_length=4,
        choices=COMMISSION_TIERS,
        default='own',
        help_text='The commission book and ledger figures. An admin always sees all, whatever this says.',
    )

    def __str__(self):
        return f'Profile of {self.user}'
