"""The Cover tab (plan.md §9.4; J145, J57; old `presentation_workbook._CoverSheet` at 891f1b3): the logo (the agency's
name when there is none), the client, the title, the introduction, who prepared it, a labelled snapshot of the
executive summary when the proposal shows one, and the recommendation's words. Column A is a margin; B to H hold the
content and every text row is merged across them. Rows 1 to 5 are fixed; a cursor lays out the rest, and a gap
between two groups is a short row written only when something follows it. Never the Draft mark (J102).

"Prepared by" is the agency, with the deal's agent (`deals.rules.agent_name`: its agent of record, else its owner,
else the agency producer; OQ41) and the agency's phone and email under it. The words under "Our recommendation" are
`why.why_for`'s, line by line (J57): a line's own words under its name, or the deal-wide words once when no line has
its own. The cover image banner waits for the covers (slice 34).
"""

import io

from PIL import Image

from .. import cells
from .. import print_plan as pp
from .. import styles as s
from . import common

FIRST, LAST = 2, 8
LOGO_HEIGHT_PX = 80
LOGO_ROW_PT = 62
PARA_LIMIT = 1200
SNAPSHOT = 'Figures as of this download; they do not recalculate when counts or rates are edited.'
_DASHES = frozenset('-–—')


def paragraph_rows(text, limit=PARA_LIMIT):
    """A long paragraph as rows of at most `limit` characters: split on newlines (a blank line stays an empty row),
    then a longer line wrapped at the last space within the limit (a row stops at 409.5 points)."""
    flat = ('' if text is None else str(text)).replace('\r\n', '\n').replace('\r', '\n')
    if not flat.strip():
        return []
    rows = []
    for line in flat.split('\n'):
        pieces = []
        while len(line) > limit:
            cut = line.rfind(' ', 0, limit + 1)
            if cut <= 0:
                pieces.append(line[:limit])
                line = line[limit:]
            else:
                pieces.append(line[:cut])
                line = line[cut + 1 :]
        if line or not pieces:
            pieces.append(line)
        rows.extend(pieces)
    while rows and not rows[0].strip():
        rows.pop(0)
    while rows and not rows[-1].strip():
        rows.pop()
    return rows


def _shown(text):
    """'' for blank and for a lone dash: the file writes an empty cell, never a dash."""
    text = str(text or '').strip()
    return '' if text and set(text) <= _DASHES else text


class _Cover:
    def __init__(self, sheet, facts):
        self.sheet, self.facts = sheet, facts
        self.row, self.gap = 5, False

    def claim(self):
        if self.gap:
            self.row += 1
            cells.spacer(self.sheet, self.row)
            self.gap = False
        self.row += 1
        return self.row

    def merged(self, row, text, *, font, align, height=None, border=None, fill=None, first=FIRST, last=LAST):
        cells.text(self.sheet, row, first, text, font=font, fill=fill, border=border, align=align)
        cells.merge_pair(self.sheet, row, first, last)
        if height is not None:
            self.sheet.heights[row] = height

    def paragraphs(self, rows):
        for chunk in rows:
            self.merged(self.claim(), chunk, font=s.BODY, align=s.LEFT_TOP, height=cells.row_height([(chunk, 100)]))

    def agency_name(self):
        return self.facts.agency['name'] or 'Vantage Risk Solutions'

    def logo(self, row):
        data = self.facts.logo
        if data:
            width, height = Image.open(io.BytesIO(data)).size
            scale = LOGO_HEIGHT_PX / height if height else 1
            self.sheet.images.append(
                {'row': row, 'col': FIRST, 'data': data, 'name': 'logo.png', 'x_scale': scale, 'y_scale': scale}
            )
        else:
            self.merged(row, self.agency_name(), font=s.COVER_AGENCY, align=s.LEFT)
        self.sheet.heights[row] = LOGO_ROW_PT

    def title(self):
        if self.facts.title:
            return self.facts.title
        lead = 'Renewal Benefit Plans' if self.facts.renewal else 'Proposed Benefit Plans'
        effective = common.long_date(self.facts.effective)
        return f'{lead} Effective {effective}' if effective else lead

    def prepared(self):
        agency = self.facts.agency
        contact = ' · '.join(part for part in (agency['producer'], agency['phone'], agency['email']) if part)
        for text, look in (
            (f'Prepared by {self.agency_name()}', s.BOLD),
            (contact, s.BODY),
            (agency['address'], s.BODY),
            (agency['city_state_zip'], s.BODY),
        ):
            if text:
                self.merged(self.claim(), text, font=look, align=s.LEFT, height=cells.row_height([(text, 100)]))
        self.gap = True

    def summary(self):
        """The executive summary as a snapshot of the proposal's own figures; a line's heading only where the line
        changes."""
        blocks = self.facts.summary['blocks']
        if not (self.facts.summary['on'] and blocks):
            return
        cells.band(self.sheet, self.claim(), LAST, 'Executive Summary')
        self.merged(self.claim(), SNAPSHOT, font=s.ITALIC, align=s.LEFT, height=cells.row_height([(SNAPSHOT, 100)]))
        heading = object()
        for block in blocks:
            in_line = block.get('scope') == 'line'
            if in_line and block.get('line') != heading:
                heading = block.get('line')
                if block.get('line_label'):
                    self.merged(
                        self.claim(),
                        block['line_label'],
                        font=s.BOLD,
                        fill=s.FILL_SUBHEAD,
                        border=s.THIN,
                        align=s.label_align(1),
                        height=s.ROW_H,
                    )
            self.summary_row(self.claim(), block, in_line and bool(block.get('line_label')))
        self.gap = True

    def summary_row(self, row, block, indented):
        label = str(block.get('label') or '').strip()
        value = _shown(block.get('value_label'))
        detail = ' · '.join(part for part in (_shown(block.get('delta_label')), _shown(block.get('sub'))) if part)
        for first, last, text, align in (
            (2, 4, label, s.label_align(1 if indented else 0)),
            (5, 6, value, s.CENTER),
            (7, 8, detail, s.LEFT),
        ):
            self.merged(row, text, font=s.BODY, fill=s.FILL_WHITE, border=s.THIN, align=align, first=first, last=last)
        self.sheet.heights[row] = cells.row_height([(label, 40), (value, 26), (detail, 26)])

    def recommendation(self):
        """The recommendation's words, for the lines with a tab that keep their recommendation part on."""
        lines = [line for line in self.facts.lines if common.part(line, 'recommendation') and line.presented]
        if self.facts.line_words:
            found = [(line.label, self.facts.reasons.get(line.key)) for line in lines]
            found = [(label, words) for label, words in found if words]
        else:
            words = next((self.facts.reasons.get(line.key) for line in lines if self.facts.reasons.get(line.key)), '')
            found = [('', words)] if words else []
        if not found:
            return
        cells.band(self.sheet, self.claim(), LAST, 'Our recommendation')
        for label, words in found:
            if label:
                self.merged(
                    self.claim(),
                    label,
                    font=s.BOLD,
                    fill=s.FILL_SUBHEAD,
                    border=s.THIN,
                    align=s.label_align(1),
                    height=s.ROW_H,
                )
            self.paragraphs(paragraph_rows(words))

    def write(self):
        sheet = self.sheet
        sheet.widths[1] = 2.5
        for col in range(FIRST, LAST + 1):
            sheet.widths[col] = 15.5
        cells.spacer(sheet, 1)
        self.logo(2)
        cells.spacer(sheet, 3)
        self.merged(
            4,
            self.facts.client,
            font=s.COVER_NAME,
            align=s.LEFT,
            height=cells.row_height([(self.facts.client, 48)], line_pt=25),
        )
        title = self.title()
        self.merged(5, title, font=s.COVER_TITLE, align=s.LEFT, height=cells.row_height([(title, 36)], line_pt=33))
        self.gap = True
        intro = paragraph_rows(self.facts.intro)
        if intro:
            self.paragraphs(intro)
            self.gap = True
        self.prepared()
        self.summary()
        self.recommendation()
        return self.row


def write(sheet, ctx):
    last_row = _Cover(sheet, ctx.facts).write()
    sheet.zoom = s.ZOOM
    pp.fitted(sheet, LAST, last_row, best_fit=True)
