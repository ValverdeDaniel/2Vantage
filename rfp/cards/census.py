"""The packet's census rows (plan.md §8.12, §9.10; K34–K41). Pure over the request, its route and the census counts.

One row per census file in the one key space: each format's workbook, and Angle's CSV as its own indented row, off on
purpose ("The same census as the workbook above, saved for their portal upload", K40). Each row: the carrier and the
format's name, its columns, its format, who it is for (K36: the picked carriers; Warner's universal census "Any
carrier" when nobody is named), the rows it would carry, whether it is in the packet, its default, and the notes the
grid prints (K37: "your pick", "Off on purpose — …", "Ticked by hand — …"). With nobody on the census a row is
unavailable, "No census yet", and cannot be ticked (K41). The caps (K97) say how many people would not fit.
"""

from ..formats import definitions, scope
from . import include as ticks

NO_CENSUS = 'No census yet'


def rows(request, route, members):
    """[card] in definition order, an alternate format after its workbook. `members` = employees + dependents."""
    defaults = scope.defaults(request, route)
    picked = ticks.resolved(request.get('include'), defaults)
    taken = scope.recipients(request)
    available = members > 0
    out = []
    for fmt_key, fmt in definitions.DEFINITIONS.items():
        primary = scope.file_key(fmt)
        for kind in fmt['formats']:
            key = scope.file_key(fmt, kind)
            cap = fmt['max_rows'] if kind == 'xlsx' else 0
            out.append(
                {
                    'key': key,
                    'kind': 'census',
                    'format_key': fmt_key,
                    'alt_of': '' if key == primary else primary,
                    'carrier': fmt['carrier'],
                    'label': fmt['label'],
                    'version': fmt['version'],
                    'file_format': kind,
                    'columns': len(fmt['columns']),
                    'include': picked[key] and available,
                    'default_include': defaults[key],
                    'deliberate': scope.deliberate(key),
                    'available': available,
                    'reason': '' if available else NO_CENSUS,
                    'required_by': list(taken.get(fmt_key, [])),
                    'universal': fmt_key == definitions.UNIVERSAL,
                    'rows': members,
                    'max_rows': cap or None,
                    'capped': bool(cap and members > cap),
                }
            )
    return out


def block(request, route, members):
    """The packet card's census part: its rows and how many are in the packet."""
    found = rows(request, route, members)
    return {'rows': found, 'count': sum(1 for row in found if row['include'])}
