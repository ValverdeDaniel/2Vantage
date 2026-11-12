"""The packet card's one list (plan.md §8.12, §9.10; K34–K56; K.6 "the one card list"). Pure over one request.

`rows(ctx)` is every row the grid draws, in the old page's sections and order — carrier census formats, Warner's
forms with the census inside (download only), questionnaires & disclosures, the request form & proposal documents,
attachments from the file — each with its tick resolved: the stored tick where one differs from the default, else the
default (K35); a row that cannot be built is never in. The packet zip, the email drafts and the check all read this
list, so what is ticked on screen is exactly what leaves (old `export_cards`). `defaults(ctx)` is what the service
keeps ticks against; `block(ctx)` is what the page draws, with "N documents in the packet" and the members' names
(K55), the "Not set up" notices (K45) and the section titles.
"""

from ..audience import receives
from ..formats import bundled, definitions, scope
from . import census, docs, forms
from . import include as ticks

SECTIONS = (
    ('census', 'Carrier census formats'),
    ('census_forms', 'Warner quote request forms with the census inside'),
    ('questionnaires', 'Carrier questionnaires & disclosures'),
    ('documents', 'Request form & proposal documents'),
    ('attachments', 'Attachments from the file'),
)
OTHER_CARRIERS = scope.OTHER_CARRIERS
CSV_ROW_BYTES = 200
LEAD = ('cover', 'form')


def _census_rows(ctx):
    out = []
    for row in census.rows(ctx.stored, ctx.route, ctx.members):
        fmt = definitions.DEFINITIONS[row['format_key']]
        csv = row['file_format'] == 'csv'
        out.append(
            {
                **row,
                'section': 'census',
                'title': f'{row["carrier"]} census' + (' (CSV for their portal)' if csv else ''),
                'sub': '',
                'packet_eligible': True,
                'hint': '',
                'for_fallback': 'Any carrier' if row['universal'] and not row['alt_of'] else '—',
                'lens': row['alt_of'] or row['key'],
                'phi': True,
                'size': ctx.members * CSV_ROW_BYTES if csv else len(bundled.raw(fmt['file'])),
            }
        )
    return out


def _named(rows):
    for row in rows:
        row.setdefault('title', row['label'])
    return rows


def all_rows(ctx):
    """Every row with its default tick, before the stored ticks are laid over it."""
    return _named(
        _census_rows(ctx)
        + forms.census_forms(ctx)
        + docs.questionnaires(ctx)
        + forms.lead(ctx)
        + [docs.proposal(ctx)]
        + docs.attachments(ctx)
    )


def defaults(ctx, found=None):
    """{key: ticked by default} over every row that can ride the packet."""
    found = all_rows(ctx) if found is None else found
    return {row['key']: row['default_include'] for row in found if row['packet_eligible']}


def _audience(ctx, found):
    """Who a questionnaire or a file carrying member data reaches on a direct request (OQ66; G112)."""
    if ctx.route != 'direct':
        return
    asked = [(key, ctx.chip[key]['name']) for key in ctx.picked]
    if ctx.other_text():
        asked.append((None, OTHER_CARRIERS))
    for row in found:
        if row['section'] == 'questionnaires' or (row['section'] == 'attachments' and row['phi']):
            row['required_by'] = [name for key, name in asked if receives(row, key, ctx)]


def rows(ctx):
    found = all_rows(ctx)
    ticked = ticks.resolved(ctx.stored['include'], defaults(ctx, found))
    for row in found:
        row['include'] = bool(ticked.get(row['key'])) and bool(row['available']) and row['packet_eligible']
    _audience(ctx, found)
    return found


def in_packet(found):
    """The ticked rows, the cover that leads first (K47: Warner's form or ours), then the grid's order."""
    ticked = [row for row in found if row['include']]
    return [row for row in ticked if row['key'] in LEAD] + [row for row in ticked if row['key'] not in LEAD]


def block(ctx, found=None):
    found = rows(ctx) if found is None else found
    packed = in_packet(found)
    return {
        'count': len(packed),
        'members': [row['title'] for row in packed],
        'rows': found,
        'notices': docs.notices(ctx),
        'sections': [{'key': key, 'title': title} for key, title in SECTIONS],
    }
