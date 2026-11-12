"""/api/meta/ `rfp` (plan.md §7.1, K.6): the RFP tab's words and vocabularies, so the browser holds none (rule 1).
Format keys and labels join with slice 45, the form variants with slice 46."""

from deals import carriers as identities

from . import carriers, cleaners, request, services

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
    }
