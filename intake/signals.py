"""Signals intake sends to apps to its right (plan.md §3.3, O.1).

- `coverage_changed(deal_id)`: sent inside the write's transaction, after the Deal and intake's rows are locked, when
  the lines to quote or a current-coverage row changed — what census needs to know about the deal's required columns
  (§5.3.3: the requested lines' tiers, and the current medical plan while medical is in force). census answers by
  rewriting its stored counts in the same transaction (O.3.7: the Deal, intake, then census rows).
"""

from django.dispatch import Signal

coverage_changed = Signal()  # kwargs: deal_id


def announce(deal_id):
    coverage_changed.send(sender='intake', deal_id=deal_id)
