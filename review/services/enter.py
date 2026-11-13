"""Edit mode on the request page: answers read over the phone, typed in by us (plan.md §7.13 `POST review/enter/`;
L34, L35; old 891f1b3 `RequestPage.jsx` edit mode, `review.enter`). Review owns no values: each answer goes through its
owner's typed write — the intake's `update_answers`, the census's `edit_values` — with origin `relay` when "These came
from the client" is on (saved as the client's, entered by us) or `typed` when it is off.

`enter(user, deal_id, answers, origin=)`: `answers` {ref: value}, refs `intake:<question>`, `census:<member
id>:<column>` (never SSN, never a person a client added and nobody approved) and (slice 58, G79: "Enter it", "From the
client — entered by us") `q:<form>:<slot>` through the questionnaire's `set_answers(relay=…)`. One transaction, the
Deal first, then the owners in chain order (the intake, the people by id, then the forms), as their own services
lock; an unchanged value writes nothing, '' clears a value (clearing a box takes our typed value back off). A typed or
relayed write closes a client's answer waiting on the same slot as `replaced` (the owners do it, Ch. 13d). Returns
Entered(saved [ref], activity ids). 400 naming the refs it cannot take; the owners' own refusals (a value they reject,
a person gone) pass through.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from census import fields as census_fields
from census.models import Member
from census.services import edit_values
from deals.models import Deal
from intake import form
from intake.services import update_answers
from questionnaire.services import set_answers as set_form_answers

from ..rules import refs as ref_rules

Entered = namedtuple('Entered', 'saved activity_ids')

ORIGINS = ('typed', 'relay')
LIMIT = 500
NOTHING = 'Send the answers as an object of refs.'
CANNOT = 'Edit mode cannot take these: {refs}.'


def _split(deal, answers):
    """({key: value}, {member id: {column: value}}, {form: {slot: value}}), or a 400 naming the refs it cannot
    take."""
    intake, census, forms, bad = {}, {}, {}, []
    for ref, value in answers.items():
        if not isinstance(value, str | int | float | list) or isinstance(value, bool):
            bad.append(ref)
            continue
        found = ref_rules.note_of(ref)
        if found and found[0] == 'questionnaire' and ':' in found[1] and not isinstance(value, list):
            form_key, _, slot = found[1].partition(':')
            forms.setdefault(form_key, {})[slot] = str(value)
        elif found and found[0] == 'intake' and found[1] in form.ANSWER_KEYS:
            intake[found[1]] = value
        elif (
            found and found[0] == 'census' and found[2] is not None and found[1] in census_fields.BY_KEY
            and found[1] not in census_fields.SSN_KEYS
        ):  # fmt: skip
            census.setdefault(found[2], {})[found[1]] = value
        else:
            bad.append(ref)
    known = set(Member.objects.filter(deal_id=deal.id, pk__in=list(census)).values_list('pk', flat=True))
    bad += [f'census:{member}:{column}' for member in census if member not in known for column in census[member]]
    if bad:
        raise ValidationError({'answers': [CANNOT.format(refs=', '.join(str(ref)[:60] for ref in bad[:10]))]})
    return intake, census, forms


@transaction.atomic
def enter(user, deal_id, answers, *, origin='relay'):
    if not isinstance(answers, dict) or not answers or len(answers) > LIMIT:
        raise ValidationError({'answers': [NOTHING]})
    if origin not in ORIGINS:
        raise ValidationError({'origin': ['Send origin as typed or relay.']})
    deal = Deal.objects.select_for_update(of=('self',)).get(pk=deal_id)
    intake, census, forms = _split(deal, answers)
    saved, rows = [], []
    if intake:
        done = update_answers(user, deal.id, intake, origin=origin)
        saved += [f'intake:{key}' for key in done.changed]
        rows.append(done.activity)
    for member_id in sorted(census):
        done = edit_values(user, member_id, census[member_id], origin=origin)
        saved += [f'census:{member_id}:{key}' for key in done.changed]
        rows.append(done.activity)
    for form_key, part in forms.items():
        done = set_form_answers(user, deal.id, form_key, part, relay=origin == 'relay')
        saved += [f'q:{form_key}:{key}' for key in done.changed if not key.startswith('cleared:')]
        rows.append(done.activity)
    ids = list(dict.fromkeys(row.id for row in rows if row is not None))
    return Entered(saved, ids)
