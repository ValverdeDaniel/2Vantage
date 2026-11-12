"""/api/meta/ `rfp` (plan.md §7.1, K.6): the RFP tab's words and vocabularies, so the browser holds none (rule 1).
`formats` (slice 45): the census files of the one key space, each with its carrier, label, format and, for a second
format, the workbook it is saved from; the form variants join with slice 46."""

from deals import carriers as identities

from . import carriers, cleaners, request, services
from .cards import census as packet
from .formats import definitions, scope

GROUPS = ((identities.MEDICAL, 'Medical carriers'), (identities.ANCILLARY, 'Ancillary carriers'))


def meta():
    return {
        'cards': [{'key': key, 'label': label} for key, label in services.CARDS],
        'bands': [{'key': key, 'label': label} for key, label in request.BANDS],
        'routes': [
            {'key': key, 'label': label, 'long': long, 'title': title, 'tag': tag}
            for key, label, long, title, tag in request.ROUTES
        ],
        'funding': [{'key': key, 'label': label} for key, label in request.FUNDING],
        'no_funding': request.NO_FUNDING,
        'groups': [{'key': key, 'label': label} for key, label in GROUPS],
        'carriers': carriers.meta(),
        'limits': dict(cleaners.LIMITS),
        'warner_inbox': carriers.WARNER_QUOTING_EMAIL,
        'formats': formats(),
        'no_census': packet.NO_CENSUS,
    }


def formats():
    return [
        {
            'key': scope.file_key(fmt, kind),
            'format_key': fmt_key,
            'alt_of': '' if kind == fmt['formats'][0] else scope.file_key(fmt),
            'carrier': fmt['carrier'],
            'label': fmt['label'],
            'file_format': kind,
            'universal': fmt_key == definitions.UNIVERSAL,
            'deliberate': scope.deliberate(scope.file_key(fmt, kind)),
        }
        for fmt_key, fmt in definitions.DEFINITIONS.items()
        for kind in fmt['formats']
    ]
