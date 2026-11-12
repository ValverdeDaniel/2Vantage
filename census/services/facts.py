"""Rewriting the stored counts on their own (plan.md §6.6, K.6; O.3.7).

The census's own writes rewrite `CensusFacts` inside their transaction. `refresh_facts` is the door for a change made
elsewhere that moves what is required — rfp's carrier pick calls it on commit (slice 45) — and for `rebuild_facts
--fix`: the Deal, then the facts row.
"""

from django.db import transaction

from .. import facts
from . import rows


@transaction.atomic
def refresh_facts(deal_id):
    """Rewrite the deal's CensusFacts; returns the fields that changed."""
    rows.lock_deal(deal_id)
    return facts.refresh(deal_id)
