"""Pictures a person uploads for the client files (plan.md §3.8, §6.11; J.6.7 "an images helper", ch25; B12): the
proposal's cover images and the team's photos. Ported from old Vantage 891f1b3 `pipeline/branding.py`
(`_checked_upload`, `prepare_cover`, `banner_jpeg`) and `pipeline/stock_images.py` (`_fitted`).

A picture reaches a client's file, so only a PNG or a JPEG is taken: the extension and the decoded format must both
say so (never SVG, GIF, WebP or anything that can carry script), within a byte cap and a pixel cap, and Pillow's
decompression-bomb guard stands. What is stored is never the upload: `reencode` turns it upright, lays any
transparency on white, re-encodes it as a fresh JPEG with no metadata at all (no EXIF, no text chunk, no colour
profile) and brings its long side down. `fitted` crops a stored picture to the box a page fills, also as a fresh
JPEG, through a bounded cache keyed on the stored file's name and size, so a deck build decodes each picture once.

Every refusal is a sentence the screen shows as it is; none repeats the file's name. Pure apart from the cache.
"""

import io
import threading
from collections import OrderedDict

from PIL import Image, ImageOps, UnidentifiedImageError

EXTENSIONS = ('.png', '.jpg', '.jpeg')
FORMATS = ('PNG', 'JPEG')
QUALITY = 88
FIT_QUALITY = 85
FIT_CACHE = 64
_CACHE = OrderedDict()
_LOCK = threading.Lock()


class Refused(ValueError):
    """An upload this app will not keep; the message is the producer's sentence."""


def _article(noun):
    return 'An' if noun[0] in 'aeiou' else 'A'


def checked(upload, *, max_bytes, max_side, noun='picture'):
    """An uploaded picture's bytes, or `Refused` with the reason: the name ends .png/.jpg/.jpeg, the decoded format is
    PNG or JPEG (a phone's MPO is a JPEG), the file is at most `max_bytes` and the picture at most `max_side` pixels a
    side. Only the header is decoded here; the caller re-encodes, so the upload's bytes are never stored."""
    megabytes = max_bytes // (1024 * 1024)
    name = str(getattr(upload, 'name', '') or '').lower()
    if not name.endswith(EXTENSIONS):
        raise Refused(f'{_article(noun)} {noun} must be a PNG or JPEG file.')
    size = getattr(upload, 'size', None)
    if size is not None and size > max_bytes:
        raise Refused(f'That {noun} is larger than {megabytes} MB.')
    data = upload.read()
    if len(data) > max_bytes:
        raise Refused(f'That {noun} is larger than {megabytes} MB.')
    try:
        with Image.open(io.BytesIO(data)) as probe:
            kind, (width, height) = probe.format, probe.size
    except Image.DecompressionBombError:
        raise Refused(f'That {noun} is larger than {max_side} pixels on a side.') from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise Refused('That file is not a readable PNG or JPEG image.') from None
    kind = 'JPEG' if kind == 'MPO' else kind
    if kind not in FORMATS:
        raise Refused(f'{_article(noun)} {noun} must be a PNG or JPEG file.')
    if max(width, height) > max_side:
        raise Refused(f'That {noun} is larger than {max_side} pixels on a side.')
    return data


def _rgb(data):
    """The picture upright, as RGB pixels: a 16-bit greyscale scaled to 8 bits (a plain convert would clip it to
    white), transparency laid on white (JPEG has none)."""
    with Image.open(io.BytesIO(data)) as original:
        original.load()
        picture = ImageOps.exif_transpose(original)
    if picture.mode.startswith('I'):
        picture = picture.convert('I').point(lambda value: value * (1 / 256)).convert('L')
    if picture.mode in ('RGBA', 'LA') or (picture.mode == 'P' and 'transparency' in picture.info):
        rgba = picture.convert('RGBA')
        picture = Image.new('RGB', rgba.size, (255, 255, 255))
        picture.paste(rgba, mask=rgba.getchannel('A'))
        return picture
    return picture.convert('RGB')


def _jpeg(picture, quality):
    picture.info = {}
    buffer = io.BytesIO()
    picture.save(buffer, format='JPEG', quality=quality, optimize=True)
    return buffer.getvalue()


def reencode(data, long_side, quality=QUALITY):
    """(JPEG bytes, (width, height)): the picture upright, on white, its long side at most `long_side`, no metadata."""
    try:
        picture = _rgb(data)
    except (OSError, ValueError, SyntaxError):
        # Truncated data, a mode with no RGB form, or a malformed EXIF block (exif_transpose raises SyntaxError).
        raise Refused('That file is not a readable PNG or JPEG image.') from None
    picture.thumbnail((long_side, long_side), Image.LANCZOS)
    return _jpeg(picture, quality), picture.size


def thumbnail(data, long_side):
    """A stored picture's thumbnail (JPEG bytes), its long side at most `long_side`."""
    return reencode(data, long_side, quality=FIT_QUALITY)[0]


def _box(size, aspect):
    width, height = size
    if width / height > aspect:
        return round(height * aspect), height
    return width, round(width / aspect)


def fit(data, pixels, focus=(0.5, 0.5)):
    """The picture cropped to `pixels` (w, h) around `focus` (0..1 across and down), as a fresh JPEG; never larger
    than the picture itself (a small upload is not blown up, only cropped to the box's shape)."""
    picture = _rgb(data)
    target = _box(picture.size, pixels[0] / pixels[1])
    if target[0] > pixels[0]:
        target = pixels
    picture = ImageOps.fit(picture, target, Image.LANCZOS, centering=focus)
    return _jpeg(picture, FIT_QUALITY)


def fitted(field, pixels, focus=(0.5, 0.5)):
    """A stored file's picture fitted to `pixels`, or None when the file is missing or will not open: a broken
    picture must not lose the document. Cached per (file name, file size, box), at most FIT_CACHE pictures; a replaced
    file is stored under a new name."""
    if not field:
        return None
    try:
        key = (field.name, field.size, tuple(pixels), tuple(focus))
    except Exception:  # noqa: BLE001 - a file gone from storage
        return None
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return _CACHE[key]
    try:
        with field.open('rb') as handle:
            found = fit(handle.read(), pixels, focus)
    except Exception:  # noqa: BLE001 - as the old stock_images.path_for: the page prints without it
        return None
    with _LOCK:
        _CACHE[key] = found
        while len(_CACHE) > FIT_CACHE:
            _CACHE.popitem(last=False)
    return found
