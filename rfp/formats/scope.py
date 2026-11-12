"""Which census formats the request sends, and who each is for (plan.md §5.3.3, §9.10; K36, K39, K124; OQ64). Pure
over the request's stored settings and the definitions: it reads no census.

- **Default ticks** (K39, OQ64 default): Warner's universal census is ticked when nothing is picked, the route is
  Warner, a picked carrier has no format of its own, or "Other carriers" is filled; so it leaves the packet when every
  picked carrier has its own format and "Other carriers" is empty (reversing D-063 #6). A carrier's own format is
  ticked when that carrier is picked, and, as the old app did, when nothing is picked yet. Angle's CSV is off on
  purpose: the same census as the workbook, saved for their portal.
- **For** (K36): the picked carriers a format is for; the universal one also "Other carriers".
- **Sent** (K124): the formats the request sends for a carrier: picked carriers' own formats, the universal format when
  a picked carrier or "Other carriers" takes it, and any format ticked by hand; a format unticked by hand is not sent.
"""

from deals import carriers as identities

from .. import carriers
from . import definitions

OTHER_CARRIERS = 'Other carriers'
ALT_REASON = 'The same census as the workbook above, saved for their portal upload'


def file_key(fmt, kind='xlsx'):
    """The format's key in the one key space (K.6): census-warner, census-angle, census-angle-csv, …"""
    return f'census-{fmt["file_key"]}' + ('' if kind == fmt['formats'][0] else f'-{kind}')


def keys():
    return [file_key(fmt, kind) for fmt in definitions.DEFINITIONS.values() for kind in fmt['formats']]


def _own_format(key):
    return (carriers.ATTRIBUTES.get(key) or {}).get('census_format') or ''


def recipients(request):
    """{format key: [names]}: who each format is for, from the picks (registry order) and "Other carriers"."""
    out = {}
    for key in request.get('carriers') or []:
        if key not in identities.BY_KEY:
            continue
        own = _own_format(key) or definitions.UNIVERSAL
        out.setdefault(own, []).append(identities.BY_KEY[key]['name'])
    if (request.get('other_carriers') or '').strip():
        out.setdefault(definitions.UNIVERSAL, []).append(OTHER_CARRIERS)
    return out


def defaults(request, route):
    """{file key: ticked by default} for the census rows of the packet (K39)."""
    picked = [key for key in request.get('carriers') or [] if key in identities.BY_KEY]
    taken = recipients(request)
    out = {}
    for fmt_key, fmt in definitions.DEFINITIONS.items():
        if fmt_key == definitions.UNIVERSAL:
            ticked = not picked or route == 'warner' or fmt_key in taken
        else:
            ticked = not picked or fmt_key in taken
        out[file_key(fmt)] = ticked
        for kind in fmt['formats'][1:]:
            out[file_key(fmt, kind)] = False
    return out


def deliberate(key):
    """Why a row is off on purpose ('' for none): what "Select all" leaves alone."""
    return ALT_REASON if key.endswith('-csv') else ''


def sent(request):
    """{format key: [names]} for the formats the request sends for a carrier (K124), names saying whose file it is."""
    include = request.get('include') or {}
    out = {key: list(names) for key, names in recipients(request).items()}
    for fmt_key, fmt in definitions.DEFINITIONS.items():
        ticked = include.get(file_key(fmt))
        if ticked is False:
            out.pop(fmt_key, None)
        elif ticked is True and fmt_key not in out:
            out[fmt_key] = [fmt['carrier']]
    return out
