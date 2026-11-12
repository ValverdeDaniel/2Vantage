"""The agency's default commission rate (plan.md §5.6, §6.2; H8, H100): `set_default_commission`, the one writer of
`AgencySettings.default_commission` outside Django admin. Commission's Settings tab calls it (every commission default
on one screen, H100), records the gesture in its own Activity row and reverts it through this door, as intake does with
`set_lines`; this function records nothing itself.
"""

from django.db import transaction

from .. import comp
from ..models import AgencySettings


def _stored(raw):
    found, error = comp.parse_comp(raw, allow_blank=True)
    return None if error else found


@transaction.atomic
def set_default_commission(value):
    """Store a parsed Comp (or None to clear). Returns {'default_commission': [before, after]} or {} when unchanged.
    Locks the row; the row is created on the first write (a read never creates it)."""
    row = AgencySettings.objects.select_for_update().filter(pk=1).first() or AgencySettings(pk=1)
    before = _stored(row.default_commission)
    if before == value:
        return {}
    row.default_commission = value or {}
    row.save()
    return {'default_commission': [before, value]}
