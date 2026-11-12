"""The faces the questionnaire PDFs draw in, and our own marks (G57, G53).

Answers are stamped in Arimo, the Arial-metric face bundled beside the carrier blanks with its licence
(`assets/questionnaires/Arimo.ttf`): identical advance widths to the carrier's embedded ArialMT, so a stamped value
reads like the caption beside it. A missing face is loud: a substitute would put the wrong typeface on a carrier
document. reportlab's font registry is process-wide, so registration is too, once, under a lock.

Our own marks (the DRAFT line, the e-signature caption) keep a base-14 face on purpose: they are ours, not the
carrier's. Typed signatures draw in Helvetica-Oblique, or in Arimo when the name holds a letter WinAnsi cannot encode
(reportlab would draw a black box per character).
"""

import threading

from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from deals import clock

from .. import forms

DRAFT_NOTE = 'DRAFT — not yet signed by the employer'
SIGNED_NOTE = 'Electronically signed (typed name)'
NOTE_FONT = 'Helvetica-Bold'
NOTE_SIZE = 6.5
NOTE_X, NOTE_Y, NOTE_LEADING = 18, 22, 8  # bottom-left, clear of every blank's own print
DRAFT_RED = colors.HexColor('#c1352e')
INK2 = colors.HexColor('#5a6472')
SIGN_FONT = 'Helvetica-Oblique'
SIGN_FALLBACK = 'QSignFallback'
FACE_FILE = 'Arimo.ttf'

_registered = set()
_lock = threading.Lock()


class FontMissing(Exception):
    """The bundled stamping face is missing: refuse rather than stamp in a substitute."""


def register(name, file_name=FACE_FILE):
    """Make the bundled face available to reportlab under `name`. Idempotent and thread-safe."""
    if name in _registered:
        return name
    with _lock:
        if name not in _registered:
            path = forms.asset_path(file_name)
            if path is None:
                raise FontMissing(f'The stamping font "{file_name}" is missing: no substitute face is used.')
            pdfmetrics.registerFont(TTFont(name, str(path)))
            _registered.add(name)
    return name


def sign_font(text):
    """The face for one typed name: Helvetica-Oblique when WinAnsi can encode it, else the bundled Arimo."""
    try:
        text.encode('cp1252')
        return SIGN_FONT
    except UnicodeEncodeError:
        return register(SIGN_FALLBACK)


def signed_on(stamp):
    """MM/DD/YYYY in the agency's zone: the date a hand-filler writes."""
    return clock.local(stamp).strftime('%m/%d/%Y') if stamp else ''


def notes(printed):
    """The lines our own mark prints at the foot of the signature page: DRAFT until the officer signs, then one
    "Electronically signed (typed name)" line per signer (G53)."""
    if not printed.officer:
        return [(DRAFT_NOTE, DRAFT_RED)]
    out = []
    for who, signer in (('company officer', printed.officer), ('agent', printed.agent)):
        if signer:
            out.append((f'{SIGNED_NOTE} · {signer["name"]}, {who} · {signer["date"]}', INK2))
    return out


def draw_notes(canvas, printed):
    """Draw `notes` bottom-left, the first line where the old DRAFT line sat."""
    for index, (text, colour) in enumerate(notes(printed)):
        canvas.setFont(NOTE_FONT, NOTE_SIZE)
        canvas.setFillColor(colour)
        canvas.drawString(NOTE_X, NOTE_Y - index * NOTE_LEADING, text)
