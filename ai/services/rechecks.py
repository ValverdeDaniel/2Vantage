"""✦ Ask Claude to re-check (plan.md §7.5, §10.4; D40, D93, E77, E80, F66; slice 22; the old start_flag_check).

`start_recheck` starts one `recheck` job over the open warnings an owner names (`registry.checkers`): the values given
as `refs`, the open warnings on some plans or read from some files, or, with none of them, every open warning on the
deal. Refused in words: without Claude (409), with nothing flagged there (409), past `MAX_FLAGS` (409: pick one file
or fewer plans), Opus for someone neither admin nor direct (409). The same re-check already going is returned. The
job's change set always waits for a person (`landing.on_recheck`): Claude never approves or fixes a value itself.
`scanned` is the Overview's "Double-check with AI" (M92, M93; slice 64): every value read from a file that no person
approved, open warnings first and at most the owner's cap a file, cut to `MAX_FLAGS` rather than refused.
"""

from rest_framework.exceptions import ValidationError

from deals.activity import Refused

from .. import client, kinds, pricing, registry
from .jobs import NO_OPUS, start

MAX_FLAGS = 400  # one re-check checks at most this many values
NO_CHECKER = 'Nothing re-checks those values yet.'
NOTHING = 'Nothing there is flagged for review, so there is nothing to re-check.'
NOTHING_SCANNED = 'Nothing on this deal came from a scan, so there is nothing to re-read.'
TOO_MANY = '{n} flagged values is more than one re-check takes ({most}). Pick one file, or tick fewer plans.'


def start_recheck(user, deal, *, owner='quotes', refs=None, plan_ids=None, document_ids=None, model='', scanned=False):
    """(job, created)."""
    from ..reading import may_use_opus

    if not client.available():
        raise Refused(client.NoKey.sentence)
    checker = registry.checkers.get(owner)
    if checker is None:
        raise ValidationError({'owner': [NO_CHECKER]})
    if model and (model not in pricing.READ_MODELS or (model == pricing.OPUS and not may_use_opus(user))):
        raise Refused(NO_OPUS)
    scope = {
        key: value
        for key, value in (('refs', refs), ('plan_ids', plan_ids), ('document_ids', document_ids))
        if value is not None
    }
    if scanned:
        scope['scanned'] = True
    claims = checker.claims(deal, scope)
    if not claims:
        raise Refused(NOTHING_SCANNED if scanned else NOTHING)
    if len(claims) > MAX_FLAGS and not scanned:
        raise Refused(TOO_MANY.format(n=len(claims), most=MAX_FLAGS))
    claims = claims[:MAX_FLAGS]
    documents = list(dict.fromkeys(claim['doc'] for claim in claims))
    params = {
        'refs': [claim['ref'] for claim in claims],
        **({'model': model} if model else {}),
        **({'scanned': True} if scanned else {}),
    }
    return start(user, deal, kinds.RECHECK, documents=documents, params=params, target=owner)
