"""Paper: the client PDF as it prints on US Letter (plan.md §9.7; J114, J115; old Vantage 891f1b3
`pipeline/proposal_paper.py`, D-196, the 2026-11-05 call's G4).

The client PDF's page is the Presentation format's 16:9 slide (`layout.tokens.DECK_SIZE`, 13.33 × 7.5 in). A Letter page
prints as it is; any other page is placed on a Letter sheet of its own orientation, scaled to fit inside a half-inch
margin and centred, as printing the PowerPoint or the PDF to fit the page on Letter does. A 16:9 slide therefore prints
at 75%, and its type three quarters as big ("9 pt prints at 6.8 pt"): Stephanie prints from PowerPoint because a PDF's
type comes out too small, so the Export viewer's Paper view says so before anyone prints.

One placement for every Letter file: the Paper view (`summary`, in the deck preview) and the Letter PDF (`letter`): a
draft's from the draft PDF, an issue's from its stored PDF bytes (slice 32), so it never differs from what was issued.
Pure but for pypdf's reading and writing.
"""

import io

import pypdf

LETTER_PORTRAIT = (612.0, 792.0)
LETTER_LANDSCAPE = (792.0, 612.0)
MARGIN = 36.0  # half an inch on every side
SAME_PT = 1.0  # within this many points a page already is a Letter sheet
TOLD = ('/Title', '/Author', '/Subject', '/Creator')  # what the Letter PDF keeps of the PDF's own document facts


def placement(width, height):
    """Where a `width` × `height` pt page lands on Letter: {sheet: (w, h), scale, x, y, as_is}, (x, y) its lower-left
    corner on the sheet. A Letter page, either way round, is its own sheet."""
    sheet_w, sheet_h = LETTER_LANDSCAPE if width >= height else LETTER_PORTRAIT
    if abs(width - sheet_w) <= SAME_PT and abs(height - sheet_h) <= SAME_PT:
        return {'sheet': (sheet_w, sheet_h), 'scale': 1.0, 'x': 0.0, 'y': 0.0, 'as_is': True}
    scale = min((sheet_w - 2 * MARGIN) / width, (sheet_h - 2 * MARGIN) / height)
    return {
        'sheet': (sheet_w, sheet_h),
        'scale': scale,
        'x': (sheet_w - width * scale) / 2,
        'y': (sheet_h - height * scale) / 2,
        'as_is': False,
    }


def summary(width, height):
    """How a page prints, for the Paper view: {scale (percent), sheet: landscape | portrait, as_is, inner}, `inner` the
    share of the sheet's width the page takes (the screen draws the sheet with the page inside it at that share)."""
    place = placement(width, height)
    sheet_w, sheet_h = place['sheet']
    return {
        'scale': round(place['scale'] * 100, 1),
        'sheet': 'landscape' if sheet_w > sheet_h else 'portrait',
        'as_is': place['as_is'],
        'inner': round(width * place['scale'] / sheet_w, 4),
    }


def letter(data):
    """Each page of the PDF `data` on its Letter sheet (`placement`): the file that prints, page for page."""
    reader = pypdf.PdfReader(io.BytesIO(data))
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        place = placement(float(page.mediabox.width), float(page.mediabox.height))
        if place['as_is']:
            writer.add_page(page)
            continue
        sheet = writer.add_blank_page(width=place['sheet'][0], height=place['sheet'][1])
        moved = pypdf.Transformation().scale(place['scale']).translate(place['x'], place['y'])
        sheet.merge_transformed_page(page, moved)
    told = reader.metadata or {}
    writer.add_metadata({key: str(told[key]) for key in TOLD if told.get(key) is not None})
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
