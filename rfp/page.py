"""The RFP tab's payload (plan.md §7.11, §8.12; K4, K6–K9, K17–K29): what the page draws above the packet. A GET writes
nothing and makes no row (a deal with no RfpRequest reads as the defaults).

- `client_name`: intake's legal name, else the client's name (K4, X-150).
- `request`: the settings with every default filled in: the route and the band's own (`route_default`), what is
  stored (`route_stored`), the funding and whether it is the default (`funding_default`), the carriers picked, other
  carriers, the due date and the notes.
- `band`: the size band from the one headcount (K17, K18; `quotes.facts`), with its count, where the count came
  from and whether it is an estimate; `enrollment`: the three answers to "how many are enrolled" and the warning that
  names them when they differ (K19, `quotes.facts.enrollment_check`).
- `carriers`: one chip per carrier, eligibility and its reason (K23, K24). `lines`: the requested lines (K16).
- `commission`: the text the form prints (K29): each line's rate from `commission.selectors.requested_rates` (the
  deal's agreed rate, else the agency default; H109), and whether any line's is the deal's own (`source`).
- `census`: the census line (K8). `done`: the cards' marks, each with the marker's name (K9).
- `packet`: the packet card (K34–K56, slices 45–46; `cards.packet.block`): every row in its section with its tick, its
  default and why, the members' names, the "Not set up" notices; `drafts`: the Emails card (K57–K66, K120;
  `drafts.block`): each draft, its send, what changed since (G113), the sends whose draft is gone; `checks_stamp`: when
  it moves, the page asks for the pills again (K52; `check.stamp`).
Everything below the band is read from one request (`context.Request`), so the packet, the drafts and the forms agree.
"""

from django.contrib.auth import get_user_model

from census import facts as census_facts
from deals import lines
from questionnaire import forms as questionnaire_forms
from questionnaire import rfp_rules
from questionnaire.selectors import rfp as questionnaire_rfp
from quotes.selectors.headcount import WHERE

from . import drafts, request, services
from .cards import packet
from .check.stamp import stamp
from .context import Request


def _names(ids):
    wanted = {pk for pk in ids if pk}
    if not wanted:
        return {}
    return {user.id: user.get_full_name() or user.username for user in get_user_model().objects.filter(pk__in=wanted)}


def marks(done, names=None):
    """{card: {by: name, by_id, at}} for the cards marked completed, in page order."""
    found = {card: entry for card, entry in (done or {}).items() if card in services.CARD_KEYS and entry}
    names = _names(entry.get('by') for entry in found.values()) if names is None else names
    return {
        card: {'by': names.get(entry.get('by'), ''), 'by_id': entry.get('by'), 'at': entry.get('at')}
        for card in services.CARD_KEYS
        if (entry := found.get(card))
    }


def band_block(check):
    used = check['used']
    key = request.band(used['count'])
    return {
        'key': key,
        'label': request.band_label(key),
        'count': used['count'],
        'source': used['source'],
        'estimate': bool(used['estimate']),
        'from': WHERE.get(used['source'], ''),
    }


def request_block(ctx):
    return {
        'route': ctx.route,
        'route_default': ctx.route_default,
        'route_stored': ctx.stored['route'],
        'carriers': ctx.stored['carriers'],
        'other_carriers': ctx.stored['other_carriers'],
        'funding': ctx.funding,
        'funding_default': ctx.stored['funding'] is None,
        'form': ctx.variant,
        'due_date': ctx.stored['due_date'],
        'notes': ctx.stored['notes'],
    }


def census_block(counts):
    found = census_facts.summary(counts)
    return {
        'has_roster': found['employees'] + found['dependents'] > 0,
        'employees': found['employees'],
        'dependents': found['dependents'],
        'readiness_pct': found['readiness_pct'],
        'errors': found['errors'],
    }


def changed_since(ctx, sends):
    """{draft: [sentence]} for each sent draft whose questionnaire changed since it went (G113), each form read once."""
    sent = {key: send.get('forms') or {} for key, send in sends.items() if isinstance(send, dict)}
    wanted = sorted({form for forms in sent.values() for form in forms if form in questionnaire_forms.FORMS})
    now = {form: questionnaire_rfp.sent_with(ctx.deal, form) for form in wanted}
    out = {}
    for key, forms in sent.items():
        out[key] = [
            f'The {questionnaire_forms.FORMS[form]["title"]} changed since this email was sent.'
            for form, then in sorted(forms.items())
            if form in now and rfp_rules.changed_since(then, now[form])
        ]
    return out


def request_parts(ctx):
    """The blocks a request edit redraws: the settings, the chips, the packet, the drafts, the marks, the stamp."""
    rows = packet.rows(ctx)
    sends = dict((ctx.row.sends if ctx.row else None) or {})
    done = (ctx.row.done if ctx.row else None) or {}
    people = [entry.get('by') for entry in done.values() if entry] + [s.get('by') for s in sends.values() if s]
    names = _names(people)
    return {
        'request': request_block(ctx),
        'carriers': ctx.chips,
        'packet': packet.block(ctx, rows),
        'drafts': drafts.block(ctx, packet.in_packet(rows), sends, names, changed_since(ctx, sends)),
        'done': marks(done, names),
        'checks_stamp': stamp(ctx),
    }


def commission_block(ctx):
    text, breakdown = ctx.commission
    sources = {rate['source'] for rate in ctx.rates.values()}  # 'deal' and/or 'agency'
    source = 'deal' if 'deal' in sources else 'agency' if sources else ''
    return {'text': text, 'breakdown': breakdown, 'source': source}


def page(deal):
    ctx = Request(deal)
    check = ctx.check
    return {
        'deal_id': deal.id,
        'client_name': ctx.group_name,
        **request_parts(ctx),
        'band': band_block(check),
        'enrollment': {key: check[key] for key in ('intake', 'census', 'advisor', 'differ', 'warning')},
        'lines': [{'key': line, 'label': lines.label(line)} for line in ctx.lines],
        'commission': commission_block(ctx),
        'census': census_block(ctx.census),
    }
