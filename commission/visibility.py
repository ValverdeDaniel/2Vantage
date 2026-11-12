"""Who sees which booked figures (plan.md §5.6 "Who sees what"; H102, OQ73's default; H.6 `visibility.py`). Used only by
the ledger's reads and exports: the deal tab's rates, expected figure and split terms are every deal user's (D-066).

- The all tier (every admin) sees every record and every share.
- The own tier (a producer's default) sees the records it holds a share in (`party_ids`), and on them its own share
  only: the other shares are collapsed away (H102).
- The none tier sees no ledger figure.
"""

from accounts.access import commission_tier

from .models import Party

ALL, OWN, NONE = 'all', 'own', 'none'


class Viewer:
    """The viewer's tier and Party, read once per request."""

    def __init__(self, user):
        self.user = user
        self.tier = commission_tier(user)
        self.party_id = (
            Party.objects.filter(user_id=user.id).values_list('id', flat=True).first()
            if self.tier == OWN and getattr(user, 'is_authenticated', False)
            else None
        )

    @property
    def all(self):
        return self.tier == ALL

    @property
    def sees_ledger(self):
        return self.tier in (ALL, OWN)


def scoped(records, viewer):
    """The records the viewer may see (a queryset)."""
    if viewer.all:
        return records
    if viewer.tier == OWN and viewer.party_id:
        return records.filter(party_ids__contains=[viewer.party_id])
    return records.none()


def visible_shares(shares, viewer):
    """The shares the viewer may see on a record they can see: all of them, or their own only."""
    if viewer.all:
        return shares
    if viewer.tier == OWN and viewer.party_id:
        return [share for share in shares if share['party'] == viewer.party_id and share['role'] != 'house']
    return []
