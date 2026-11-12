"""Who is asked, for what, and which files reach whom (plan.md §9.11; K39, K61, K104; G112; OQ64, OQ66). Pure over one
request (`context.Request`).

- `asked_for(ctx, draft)`: who a draft asks and for which lines — the record a send stores beside its date, which the
  proposal's Markets checked reads (`selectors.asked_by_line`; K64, K117). Through Warner one email reaches every
  picked carrier and each name in "Other carriers"; direct, a carrier's draft asks that carrier alone and the "Other
  carriers" draft each typed name. A carrier is asked for the requested lines it quotes at the band; one with no column
  at the band was still named, so it is asked for the lines it quotes at any size, else for every requested line. A
  typed name the registry knows is that carrier; one it does not is kept by name (old `rfp_email.asked_for`).
- `receives(card, carrier, ctx)`: whether a ticked file rides a direct draft. `carrier` is a registry key, or None for
  a name typed into "Other carriers". The cover goes to everyone; Warner's form only to Warner; a carrier gets its own
  census format, else the universal one (K39); a questionnaire follows `takes` (G112); a file carrying member data goes
  only to a carrier quoting one of the lines it covers, to a medical carrier when it names no line, and never to "Other
  carriers" (OQ66); a paper questionnaire follows its form's `takes`.
"""

from deals import carriers as identities
from questionnaire import forms as questionnaire_forms
from questionnaire import rfp_rules

from . import carriers
from .formats import definitions

WARNER, OTHER = 'warner', 'other'
PAPER_FORM_KINDS = {'questionnaire': questionnaire_forms.MEDICAL, 'stop_loss': questionnaire_forms.STOP_LOSS_KIND}


def quoting_lines(ctx, key):
    """The requested lines a registry carrier is asked for (see `asked_for`)."""
    row = ctx.chip.get(key)
    if row and row['lines']:
        return list(row['lines'])
    known = set(carriers.lines_for(key, 'small')) | set(carriers.lines_for(key, 'large'))
    return [line for line in ctx.lines if line in known] or list(ctx.lines)


def _registry(ctx, key):
    return {'key': key, 'name': identities.BY_KEY[key]['name'], 'lines': quoting_lines(ctx, key)}


def others(ctx):
    """The names typed into "Other carriers", each as asked."""
    out = []
    for name in identities.split_names(ctx.other_text()):
        key = identities.match(name)
        if key:
            quotable = carriers.lines_for(key, ctx.band)
            lines = [line for line in ctx.lines if line in quotable] or quoting_lines(ctx, key)
            out.append({'key': key, 'name': identities.BY_KEY[key]['name'], 'lines': lines})
        else:
            out.append({'key': None, 'name': name, 'lines': list(ctx.lines)})
    return out


def asked_for(ctx, draft):
    if draft == WARNER:
        entries = [_registry(ctx, key) for key in ctx.picked] + others(ctx)
    elif draft == OTHER:
        entries = others(ctx)
    else:
        entries = [_registry(ctx, draft)] if draft in identities.BY_KEY else []
    out, seen = [], set()
    for entry in entries:
        token = entry['key'] or identities.identity(entry['name'])
        if token and token not in seen:
            seen.add(token)
            out.append(entry)
    return out


def _medical(carrier):
    return bool(carrier) and identities.BY_KEY.get(carrier, {}).get('group') == identities.MEDICAL


def member_data_goes(card_lines, carrier, ctx):
    """OQ66: a carrier quoting one of the file's lines; with no lines, a medical carrier; never "Other carriers"."""
    if not carrier:
        return False
    if not card_lines:
        return _medical(carrier)
    return bool(set(card_lines) & set(quoting_lines(ctx, carrier)))


def _armed(ctx, kind):
    return next((entry['form'] for entry in ctx.forms if questionnaire_forms.FORMS[entry['form']]['kind'] == kind), '')


def receives(card, carrier, ctx):
    key, section = card['key'], card['section']
    if key == 'cover':
        return True
    if key == 'form' or section == 'census_forms':
        return False
    if section == 'census':
        own = (carriers.ATTRIBUTES.get(carrier) or {}).get('census_format') if carrier else ''
        return card['format_key'] == (own or definitions.UNIVERSAL)
    if section == 'questionnaires':
        return rfp_rules.takes(questionnaire_forms.FORMS[card['form']], carrier)
    if section == 'attachments' and card.get('doc_kind') in PAPER_FORM_KINDS:
        form = _armed(ctx, PAPER_FORM_KINDS[card['doc_kind']])
        if form:
            return rfp_rules.takes(questionnaire_forms.FORMS[form], carrier)
    if card.get('phi'):
        return member_data_goes(card.get('lines') or [], carrier, ctx)
    return True
