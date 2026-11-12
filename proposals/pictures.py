"""The pictures a deal's client files wear (plan.md §9.4, §9.5; J33, J35, J123, J145; old Vantage 891f1b3
`stock_images.pictures_of`/`path_for`, `branding.cover_image_for`, `presentation_content.document_cover` and the
spreadsheet's banner). Reads only: one query for the firm's uploads a deal names.

- The dark pages (cover, agenda, section dividers, thank-you) wear a stock picture by its pre-cropped name
  (`stock:<key>`, J.5 B12), or one of the firm's uploads (`CoverImage`) fitted to the page's box at about 200 dpi and
  carried as bytes in the deck's `sources`, never as a path.
- The cover wears its upload (`output.cover.image`) when it has one, else its place's pick; with the cover page off
  there is no cover and no banner. An upload deleted since the deal picked it prints its stock pick on the cover and
  no picture elsewhere, as a broken file does.
- The client spreadsheet's banner is the cover's upload alone: stock pictures never reach the spreadsheet.
"""

from documents import images

from . import catalog, config
from .layout import tokens
from .models import CoverImage

PIXELS_PER_POINT = 200 / 72
BANNER_PX = (790, 198)  # old `presentation_workbook.BANNER_PX`, drawn from a picture twice the size
STOCK_THUMB_PX = (336, 224)


def _pixels(box):
    return round(box[2] * PIXELS_PER_POINT), round(box[3] * PIXELS_PER_POINT)


BOXES = {
    'cover': _pixels(tokens.PICTURE_BOX),
    'agenda': _pixels(tokens.AGENDA_PICTURE_BOX),
    'sections': _pixels(tokens.PICTURE_BOX),
    'closing': _pixels(tokens.PICTURE_BOX),
}


def picks(stored):
    """{place: stock key, "upload:<id>" or None} for every place, the cover's upload in the cover's place."""
    found = config.output(stored)
    out = dict(found['pictures'])
    if not found['cover']['on']:
        out['cover'] = None
    elif found['cover']['image']:
        out['cover'] = f'{catalog.UPLOAD_PREFIX}{found["cover"]["image"]}'
    return out


def _uploads(chosen):
    ids = {catalog.upload_id(key) for key in chosen if catalog.upload_id(key)}
    return {image.pk: image for image in CoverImage.objects.filter(pk__in=ids)} if ids else {}


def sources_for(stored, sources):
    """{place: the src a page draws, or None}; an upload's fitted bytes go into `sources` under that src."""
    chosen = picks(stored)
    uploads = _uploads(chosen.values())
    stock = catalog.picture_sources({place: key for place, key in chosen.items() if key in catalog.STOCK_KEYS})
    out = {}
    for place, key in chosen.items():
        number = catalog.upload_id(key)
        if number is None:
            out[place] = stock.get(place)
            continue
        found = uploads.get(number)
        data = images.fitted(found.image, BOXES[place]) if found else None
        if data:
            src = f'upload:{number}:{place}'
            sources[src] = data
            out[place] = src
        elif place == 'cover':  # gone: the cover keeps its stock pick (old `cover_image_for` falls back)
            fallback = config.get(stored, 'output.pictures.cover')
            out[place] = catalog.picture_sources({place: fallback}).get(place)
        else:
            out[place] = None
    return out


def cover_upload(stored):
    """The cover's upload (a CoverImage with its file), or None: none picked, deleted since, or the cover off."""
    found = config.output(stored)['cover']
    if not (found['on'] and found['image']):
        return None
    return CoverImage.objects.filter(pk=found['image']).first()


def banner(stored):
    """The client spreadsheet's Cover banner: the cover's upload cropped to twice BANNER_PX, as JPEG bytes, or None."""
    found = cover_upload(stored)
    return images.fitted(found.image, (2 * BANNER_PX[0], 2 * BANNER_PX[1])) if found else None


def stock_thumbnail(key):
    """A stock picture's tile for the Pictures card (JPEG bytes), or None for an unknown key."""
    if key not in catalog.STOCK_KEYS:
        return None
    try:
        data = (tokens.ASSETS / 'stock_images' / f'{key}.jpg').read_bytes()
    except OSError:
        return None
    return _stock_thumb(key, data)


_THUMBS = {}


def _stock_thumb(key, data):
    if key not in _THUMBS:
        _THUMBS[key] = images.fit(data, STOCK_THUMB_PX)
    return _THUMBS[key]
