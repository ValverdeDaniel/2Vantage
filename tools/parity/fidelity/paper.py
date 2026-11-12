"""Paper, the Letter PDF (2Vantage slice 30 `paint/paper.py`; old Vantage 891f1b3 `pipeline/proposal_paper.py`, D-196):
each 16:9 page of the client PDF placed on a US Letter sheet of its own orientation, scaled into a half-inch margin and
centred. Both apps place a page by this one rule, so the lane reads each sheet's words back at the page's own size and
place: the PDF's tolerances, its footer page-number corner and the register's entries then read the same on Paper as
on the PDF, and a page placed anywhere else still shows as moved. The page picture is compared on the sheet, as it
prints.
"""

DECK = (960.0, 540.0)  # the Presentation format's page, both apps' client PDF
LETTER_PORTRAIT = (612.0, 792.0)
LETTER_LANDSCAPE = (792.0, 612.0)
MARGIN = 36.0
SAME_PT = 1.0


def placement(width, height):
    """Where a `width` × `height` page lands on Letter: {sheet, scale, x, top}, `top` from the sheet's top; None when
    the page already is a Letter sheet (it prints as it is)."""
    sheet_w, sheet_h = LETTER_LANDSCAPE if width >= height else LETTER_PORTRAIT
    if abs(width - sheet_w) <= SAME_PT and abs(height - sheet_h) <= SAME_PT:
        return None
    scale = min((sheet_w - 2 * MARGIN) / width, (sheet_h - 2 * MARGIN) / height)
    return {'sheet': (sheet_w, sheet_h), 'scale': scale, 'x': (sheet_w - width * scale) / 2,
            'top': (sheet_h - height * scale) / 2}  # fmt: skip


def unplaced(page, slide=DECK):
    """A sheet's words moved back onto the page placed on it ({size: the page's, lines, place}); a sheet that is not
    the page's Letter sheet stays as it is, so its size tells the difference."""
    place = placement(*slide)
    if place is None or any(abs(a - b) > SAME_PT for a, b in zip(page['size'], place['sheet'], strict=True)):
        return page
    scale, x, top = place['scale'], place['x'], place['top']

    def back(box):
        return ((box[0] - x) / scale, (box[1] - top) / scale, (box[2] - x) / scale, (box[3] - top) / scale)

    lines = [[(word, back(box)) for word, box in line] for line in page['lines']]
    return {'size': slide, 'lines': lines, 'place': (scale, x, top)}


def on_sheet(page, box):
    """A box on an unplaced page, back where it prints on its sheet (for the page picture)."""
    if 'place' not in page:
        return box
    scale, x, top = page['place']
    return (box[0] * scale + x, box[1] * scale + top, box[2] * scale + x, box[3] * scale + top)
