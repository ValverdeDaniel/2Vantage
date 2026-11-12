"""The client PDFs compared (Q.5): the page count and sizes; per page its fonts, its words in reading order, each
word's box (±0.5 pt; a word nudged within a few points is told apart from one the layout moved), and, where the
words agree, its picture at 110 DPI (at most 0.05% of pixels may differ).

Words come from poppler (`pdftotext -bbox-layout`) and are read top to bottom, left to right (lines by baseline), so
two files that draw the same page in a different order still read the same. Each line is masked whole (`mask.line`)
before it is split back into words, so "Prepared November 12, 2026" reads "Prepared <date>" on both sides. Pages are
lined up by their first line (the slide title), so a page one file adds is one difference, not a shift.

`compare(old_path, new_path, work, sheets=False)` → [{where, kind, old, new}]; `work` is a scratch folder for the page
pictures; `sheets` compares Paper, the Letter PDF, page by page as the PDF (`paper.py`).
"""

import difflib
import html
import re
import subprocess
from pathlib import Path

from pypdf import PdfReader

from . import align, mask, paper, pictures

BOX_TOLERANCE = 0.5  # points
# A word nudged at most this far (dx, dy in points) sits where the old one did, give or take its spacing and baseline
# (`word-offset`); anything further moved with the layout around it (`word-position`): a row added above, a re-wrap.
NUDGE = (5.0, 2.0)
LINE_GAP = 2.0  # points between baselines that still read as one line
PAGE_NUMBER_BOX = (60.0, 24.0)  # the footer corner a page number sits in: points from the right and the bottom
# A masked line is left out of the page picture whole, with what is drawn just around its words: the Draft mark's
# badge (layout.furniture.draft_items, the old `proposal_furniture` one) is a 22 pt box 12 pt wider than its words on
# each side, its top 5 pt over the line's, which pdftotext's word box starts 2.7 pt lower (the font's ascent): 7.7 pt
# above the words and 4.2 pt below them. Each side gets 1.5 pt more for the anti-aliased edge, so a page that has the
# badge (a draft) and one that has none (an issued file, slice 32) agree. (left, top, right, bottom) in points.
MASK_MARGIN = (14.0, 9.5, 14.0, 7.0)
_PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)
_WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', re.S)


def _pages(path):
    """[{size, lines: [[(text, box)]]}] in reading order."""
    raw = subprocess.run(['pdftotext', '-bbox-layout', str(path), '-'], capture_output=True, check=True).stdout
    pages = []
    for match in _PAGE.finditer(raw.decode('utf-8', 'replace')):
        words = [
            (html.unescape(w[4]), tuple(float(v) for v in w[:4])) for w in _WORD.findall(match.group(3)) if w[4].strip()
        ]
        words.sort(key=lambda item: (item[1][3], item[1][0]))
        lines, current, base = [], [], None
        for word in words:
            if base is not None and word[1][3] - base > LINE_GAP:
                lines.append(sorted(current, key=lambda item: item[1][0]))
                current = []
            if not current:
                base = word[1][3]
            current.append(word)
        if current:
            lines.append(sorted(current, key=lambda item: item[1][0]))
        pages.append({'size': (float(match.group(1)), float(match.group(2))), 'lines': lines})
    return pages


def _numbered(page):
    """The page with its footer page number read as <page>: a page one file adds renumbers every page after it,
    which the page alignment already reports once. The number is right-aligned, so it is placed by its right edge (its
    box shrunk to that edge): 9 and 10 end at the same point but start a digit apart."""
    width, height = page['size']
    lines = []
    for line in page['lines']:
        lines.append([
            ('<page>', (box[2], box[1], box[2], box[3])) if word.isdigit() and box[0] > width - PAGE_NUMBER_BOX[0]
             and box[1] > height - PAGE_NUMBER_BOX[1] else (word, box)
            for word, box in line
        ])  # fmt: skip
    return {**page, 'lines': lines}


def _tokens(page):
    """[(word, box | None)]: each line masked whole; a masked line's words keep no box."""
    out = []
    for line in _numbered(page)['lines']:
        text = ' '.join(word for word, _box in line)
        masked = mask.line(text)
        if masked == ' '.join(text.split()):
            out.extend(line)
        else:
            out.extend((word, None) for word in masked.split())
    return out


def _masked_boxes(page):
    """One box (points, with MASK_MARGIN) round each line `_tokens` masks, its words and the gaps between them: what
    the page picture leaves out."""
    boxes = []
    left, top, right, bottom = MASK_MARGIN
    for line in _numbered(page)['lines']:
        text = ' '.join(word for word, _box in line)
        if line and mask.line(text) != ' '.join(text.split()):
            x0, y0 = min(b[0] for _word, b in line), min(b[1] for _word, b in line)
            x1, y1 = max(b[2] for _word, b in line), max(b[3] for _word, b in line)
            boxes.append(paper.on_sheet(page, (x0 - left, y0 - top, x1 + right, y1 + bottom)))
    return boxes


def _title(page):
    for line in page['lines']:
        text = mask.line(' '.join(word for word, _box in line))
        if text:
            return text[:80]
    return '(no words)'


def _fonts(path):
    found = []
    for page in PdfReader(str(path)).pages:
        names = set()
        fonts = (page.get('/Resources') or {}).get('/Font') or {}
        for ref in fonts.values():
            name = str(ref.get_object().get('/BaseFont', ''))
            names.add(name.split('+', 1)[-1].lstrip('/'))
        found.append(sorted(names))
    return found


def _page_differences(where, old_page, new_page):
    out = []
    old_tokens, new_tokens = _tokens(old_page), _tokens(new_page)
    old_words, new_words = [t[0] for t in old_tokens], [t[0] for t in new_tokens]
    nudged, moved = [], []
    for o, n in align.pairs(old_words, new_words):
        if o is not None and n is not None and old_words[o] == new_words[n]:
            a, b = old_tokens[o][1], new_tokens[n][1]
            if a and b:
                dx, dy = b[0] - a[0], b[3] - a[3]
                if max(abs(dx), abs(dy)) > BOX_TOLERANCE:
                    (nudged if abs(dx) <= NUDGE[0] and abs(dy) <= NUDGE[1] else moved).append((dx, dy))
    matcher = difflib.SequenceMatcher(a=old_words, b=new_words, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != 'equal':
            out.append((where, 'words', ' '.join(old_words[i1:i2]) or None, ' '.join(new_words[j1:j2]) or None))
    for kind, found in (('word-offset', nudged), ('word-position', moved)):
        if found:
            dx = max((d[0] for d in found), key=abs)
            dy = max((d[1] for d in found), key=abs)
            out.append((where, kind, f'{len(found)} words', f'dx up to {dx:+.1f} pt, dy up to {dy:+.1f} pt'))
    if old_page['size'] != new_page['size']:
        out.append((where, 'page-size', old_page['size'], new_page['size']))
    return out


def compare(old_path, new_path, work, sheets=False):
    """`sheets` for Paper: each Letter sheet's words read back on the page placed on it (`paper.unplaced`)."""
    old, new = _pages(old_path), _pages(new_path)
    if sheets:
        old, new = [paper.unplaced(p) for p in old], [paper.unplaced(p) for p in new]
    old_fonts, new_fonts = _fonts(old_path), _fonts(new_path)
    out = []
    if len(old) != len(new):
        out.append({'where': 'pages', 'kind': 'page-count', 'old': len(old), 'new': len(new)})
    old_titles, new_titles = [_title(p) for p in old], [_title(p) for p in new]
    pairs = align.pairs(old_titles, new_titles)
    images = None
    for o, n in pairs:
        if n is None:
            out.append({'where': f'old page {o + 1}', 'kind': 'page-removed', 'old': old_titles[o], 'new': None})
            continue
        if o is None:
            out.append({'where': f'page {n + 1}', 'kind': 'page-added', 'old': None, 'new': new_titles[n]})
            continue
        where = f'page {n + 1} «{new_titles[n]}»'
        found = _page_differences(where, old[o], new[n])
        if old_fonts[o] != new_fonts[n]:
            found.append((where, 'fonts', old_fonts[o], new_fonts[n]))
        if not found:
            if images is None:
                folder = Path(work)
                images = (pictures.rasterize(old_path, folder, 'old'), pictures.rasterize(new_path, folder, 'new'))
            hidden = _masked_boxes(old[o]) + _masked_boxes(new[n])
            share = pictures.differing_share(images[0][o], images[1][n], hidden)
            if share > pictures.PIXEL_TOLERANCE:
                found.append((where, 'picture', None, f'{share * 100:.3f}% of pixels differ'))
        out.extend({'where': w, 'kind': k, 'old': a, 'new': b} for w, k, a, b in found)
    return out
