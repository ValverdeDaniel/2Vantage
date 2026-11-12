"""The Cover card's tiles (plan.md §7.12 `proposal/covers/`; J32; old Vantage 891f1b3 `proposal_covers.preview_pdf` and
`ProposalCoverPreviewView`): one small PDF, a page a tile, which the browser draws with pdf.js.

Page 1 is the Presentation format's own cover ("Vantage") in the firm's colour, with sample words and the stock
picture the deal's cover wears (`picture`: a stock key, `none` for none, the default when absent); then one page per
uploaded cover image, in the firm's order, the same cover wearing that upload. The uploads come from their stored
thumbnails (≤600 px), never the full pictures (J.5 B12), and the PDF is keyed by an ETag, so the strip is rebuilt only
when the firm's colour, logo, uploads or the picture change. The six white Classic designs wait with Classic (J143).
"""

import hashlib

from deals.models import AgencySettings

from . import catalog
from .layout import furniture, items, tokens
from .models import CoverImage
from .paint import pdf
from .story import firm_read

SAMPLE = {'client': 'Client name', 'kind': '2027 Benefits Proposal', 'lines': ['Coverage effective January 1']}
LOGO = 'logo:agency'
NONE = 'none'


def picture_of(asked):
    """The stock key the first tile wears: the asked one, None for `none`, else the cover's default."""
    if asked == NONE:
        return None
    return asked if asked in catalog.STOCK_KEYS else catalog.DEFAULT_PICTURES.get('cover')


def etag(asked):
    agency = AgencySettings.objects.filter(pk=1).values_list('brand_color', 'logo').first()
    uploads = list(CoverImage.objects.order_by('created_at', 'id').values_list('id', 'thumb'))
    found = repr((agency, picture_of(asked), uploads)).encode('utf-8')
    return '"' + hashlib.sha1(found).hexdigest()[:20] + '"'


def _page(colours, logo, picture, caption):
    ground = furniture.dark_ground(colours, mark=not picture)
    placed = furniture.cover_items(SAMPLE, colours, logo_src=logo, picture=picture)
    width, height = tokens.DECK_SIZE
    label = items.one_line(width - tokens.PAGE_MARGIN, height - 26, caption, 9, tokens.WHITE, align='r')
    return {'kind': 'full', 'frames': [*ground, *placed, label], 'chrome': []}


def tiles_pdf(asked):
    """(the PDF's bytes, [tile labels]) in page order."""
    agency = AgencySettings.get()
    colours = furniture.palette(agency.brand_color)
    sources = {}
    logo = firm_read.file_bytes(agency.logo)
    if logo:
        sources[LOGO] = logo
    logo_src = LOGO if logo else None
    stock = picture_of(asked)
    pages = [_page(colours, logo_src, f'stock:{stock}' if stock else None, 'Cover: Vantage')]
    labels = ['Vantage']
    for number, image in enumerate(CoverImage.objects.order_by('created_at', 'id'), start=1):
        label = image.label or f'Your image {number}'
        thumb = firm_read.file_bytes(image.thumb)
        src = f'thumb:{image.id}'
        if thumb:
            sources[src] = thumb
        pages.append(_page(colours, logo_src, src if thumb else None, f'Cover: {label}'))
        labels.append(label)
    return pdf.draw(pages, 'Cover designs', sources), labels
