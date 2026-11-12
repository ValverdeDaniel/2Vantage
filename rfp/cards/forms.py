"""The packet's request form, cover page and Warner forms with the census inside (plan.md §8.12, §9.9; K42, K46, K47).
Pure over one request (`context.Request`). Words from old Vantage 891f1b3 `serializers/pipeline.py` (`export_cards`,
`census_form_entries`) and `CarriersTab.jsx`.

- `lead(ctx)`: the cover that leads the packet, by route (K47): Warner's own form through Warner, our cover page
  direct; the other stays on the grid, off on purpose with its reason, so "Select all" never puts Warner's form in
  front of a carrier asked directly. Direct, the cover comes first. The form row carries its variant chips (K46):
  Simplified is the standard at every size, the 2–50 and 51+ forms dimmed where the band does not fit them.
- `census_forms(ctx)`: Warner's three forms with the roster printed inside (K42): download only, never zipped (the
  packet's form is header only, so the roster never travels twice), each with its version, "standard", the band's
  reason and the 500-row cap.
"""

from ..forms import fill, maps
from . import base

FORM, COVER = 'form', 'cover'
FORM_OFF = 'Warner’s form goes only to Warner, and this deal goes direct to the carriers'
COVER_OFF = 'This deal goes through Warner, and their form is the cover'
FORM_ABOUT = (
    'Warner’s own request form, filled from the deal — group facts, the carriers and lines you picked, the commission '
    'ask and your notes.'
)
COVER_ABOUT = (
    'Our own cover page for carriers we ask directly — the group, the lines, the funding to quote, the commission ask '
    'and your notes, under our logo. It never says who else is being asked.'
)
FORM_CENSUS = 'form-census-'
NO_CENSUS = 'No census yet'


def form_card(ctx):
    direct = ctx.route == 'direct'
    return base.card(
        FORM,
        'documents',
        maps.VARIANTS[ctx.variant]['label'],
        'xlsx',
        default=not direct,
        deliberate=FORM_OFF if direct else '',
        sub=FORM_ABOUT,
        for_fallback='Warner Pacific',
        variant=ctx.variant,
        options=maps.options(ctx.band),
        size=len(fill.raw(ctx.variant)),
    )


def cover_card(ctx):
    direct = ctx.route == 'direct'
    return base.card(
        COVER,
        'documents',
        'RFP cover page',
        'pdf',
        default=direct,
        deliberate='' if direct else COVER_OFF,
        sub=COVER_ABOUT,
        for_fallback='Every carrier asked',
        size=8_000,
    )


def lead(ctx):
    form, cover = form_card(ctx), cover_card(ctx)
    return [cover, form] if ctx.route == 'direct' else [form, cover]


def census_forms(ctx):
    members = ctx.members
    out = []
    for option in maps.options(ctx.band):
        variant = option['key']
        reason = '' if option['applicable'] else f'Usually a {option["size"]} form'
        out.append(
            base.card(
                f'{FORM_CENSUS}{variant}',
                'census_forms',
                f'{option["label"]} + census',
                'xlsx',
                default=False,
                eligible=False,
                available=members > 0,
                reason=reason if members else NO_CENSUS,
                sub=f'Warner {option["version"]}',
                for_fallback='Warner Pacific',
                variant=variant,
                recommended=option['recommended'],
                applicable=option['applicable'],
                rows=members,
                max_rows=maps.CENSUS_ROWS,
                capped=members > maps.CENSUS_ROWS,
                lens='census-warner',
                phi=True,
            )
        )
    return out
