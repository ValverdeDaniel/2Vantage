"""The one rounding of money (plan.md §5.5, OQ9 b): `round_decimal`, half away from zero like Excel's ROUND.

Every figure is worked out in `Decimal`; `plain` turns a result into the JSON number the API sends (whole dollars as
an int, cents and percentages as a float). `round_money` stays only as a thin wrapper for callers that print (H.6).
"""

import math
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .. import values as cleaning


def round_decimal(amount, places=0):
    """Half away from zero, after reading any float at 15 significant digits: exactly what Excel's ROUND does."""
    if amount is None:
        return None
    if isinstance(amount, float):
        if not math.isfinite(amount):
            return None
        amount = format(amount, '.15g')
    return Decimal(amount).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def decimal(value):
    """A stored value or a count as a Decimal, or None (blank, or carrier text such as "20% after deductible")."""
    if value is None or value == '':
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(format(value, '.15g')) if math.isfinite(value) else None
    text = cleaning.number_text(value)
    try:
        return Decimal(text) if text is not None else None
    except InvalidOperation:
        return None


def plain(amount):
    """A Decimal as the API's JSON number: an int when whole, else a float; None stays None."""
    if amount is None:
        return None
    amount = Decimal(amount)
    return int(amount) if amount == amount.to_integral_value() else float(amount)


def round_money(amount, places=0):
    """`round_decimal` as a plain number, for callers that print (H.6)."""
    rounded = round_decimal(amount, places)
    if rounded is None:
        return None
    return int(rounded) if places == 0 else float(rounded)
