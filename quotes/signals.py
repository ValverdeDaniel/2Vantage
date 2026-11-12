"""quotes' on-commit signals (plan.md §3.3, O.1): how apps to the right hear about plans without quotes importing them.

- `sold_changed(deal_id, lines, user_id)`: a plan was sold or un-sold; commission books or voids (H.6).
- `plans_changed(deal_id, lines)`: plans on these lines changed (values, stars, order, slots, links, roles,
  enrollment, plans added or removed); proposals clears the lines' Plans card marks (J19, J.6.4).
Each is sent once the write's transaction commits, with `send_robust`, so a receiver that fails is logged and never
undoes the write (N.3 #6). No app receives them yet.
"""

from django.db import transaction
from django.dispatch import Signal

sold_changed = Signal()
plans_changed = Signal()


def _on_commit(signal, **kwargs):
    transaction.on_commit(lambda: signal.send_robust(sender='quotes', **kwargs), robust=True)


def changed(deal_id, lines):
    lines = sorted(set(lines))
    if lines:
        _on_commit(plans_changed, deal_id=deal_id, lines=lines)


def sold(deal_id, lines, user_id):
    _on_commit(sold_changed, deal_id=deal_id, lines=sorted(set(lines)), user_id=user_id)
