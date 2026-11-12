"""Which plans a proposal line presents, and in what column order (plan.md §5.4; F119, F120, J2, J4).

Membership is quotes' `presented()` and the order quotes' `order.layout()`: nothing here decides either. 2V's own
default list, its forced plans and its carrier sort retired in slice 7 (F.5 #27); this module goes in slice 25.
"""

from quotes import presented


def presented_for(state):
    """(the line's presented plans, in layout order; whether the line has no stars, so every plan prints)."""
    on = {plan.id for plan in presented.presented(state.data)}
    return [plan for plan in state.plans if plan.id in on], not presented.has_stars(state.data)
