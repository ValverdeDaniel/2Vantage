"""What the RFP's files print on top of `quotes.facts.group_facts` (plan.md §5.7 "Group facts"; K.6 `printed.py`; K17,
K101). Built once per file. Slice 45 prints what the census files carry: UHC's Group Info tab (19 facts) and Aetna's
AFA UW / FI UW selector; slice 46's `form_facts` adds what the request forms and the cover print: the due date, the
commission request, BOR on file (ticked, else blank: an unknown is never answered "No"), the funding boxes and the
current funding in words.

Values are typed the way a person types them into the carrier's cell (old `market/rfp._typed_count`): a count is a
number unless it keeps a leading zero (a SIC code like 0742 stays text), dates are dates. `group.enrolled` is the one
headcount the band uses (K17, bug 38), and `group.fte` the census count of full-time employees (C45). Ported from old
Vantage 891f1b3 `market/rfp.group_facts`, `_uhc_funding_token`, `_aetna_underwriting` and `UHC_QUOTE_LINES`.
"""

from datetime import date

from census import facts as census_facts
from census import rollup
from deals import lines
from intake.models import Intake
from quotes import facts as quote_facts

from . import cleaners, request, services
from .models import RfpRequest

# UHC prints one Quote / Do not Quote flag per product; two of our lines share its Life flag.
UHC_QUOTE_LINES = {
    'medical': ('medical',),
    'dental': ('dental',),
    'vision': ('vision',),
    'life': ('basic_life_add', 'voluntary_life'),
    'std': ('std', 'voluntary_std'),
    'ltd': ('ltd', 'voluntary_ltd'),
}
FUNDING_WORDS = dict(lines.FUNDING)  # the current coverage's funding as the forms print it ("Level-funded")
TYPED = ('group.sic', 'group.eligible', 'group.waiving', 'group.atne', 'group.total_employees', 'group.enrolled')


def typed_count(text):
    """A count or code as the number a person would type: text only when it is not a plain number or keeps a leading
    zero."""
    text = str(text if text is not None else '').strip()
    if text.isdigit() and not (len(text) > 1 and text.startswith('0')):
        return int(text)
    return text


def uhc_funding(funding):
    """Their list is Level Funded / Fully Insured / Both, with no ASO box, so a self-funded ask reads as Both."""
    fully = 'fully_insured' in funding
    level = 'level_funded' in funding or 'aso' in funding
    if fully and level:
        return 'Both'
    if level:
        return 'Level Funded'
    return 'Fully Insured' if fully else ''


def aetna_underwriting(funding):
    """AFA UW is Aetna Funding Advantage (their level-funded product), FI UW fully insured; asked for both, the cell
    stays blank for the reader."""
    fully = 'fully_insured' in funding
    level = 'level_funded' in funding or 'aso' in funding
    if fully and not level:
        return 'FI UW'
    if level and not fully:
        return 'AFA UW'
    return ''


def funding_asked(deal):
    """The funding the request asks for (K21, K22), with the default filled in."""
    row = RfpRequest.objects.filter(deal_id=deal.id).first()
    stored = cleaners.stored(row)['funding']
    return request.funding(stored, services.default_funding(deal) if stored is None else [])


def fte(deal, people=None):
    """Full-time employees counted off the roster at the intake's hours threshold (C45); '' with no employees."""
    answers = Intake.objects.filter(deal_id=deal.id).values_list('answers', flat=True).first() or {}
    threshold = str(answers.get('hours_threshold') or '').strip() or None
    found = rollup.fte(census_facts.people(deal.id) if people is None else people, threshold)
    return '' if found is None else found


def from_facts(group, funding, quoted, fte_count):
    """{source: value} for the census files (pure)."""
    out = {key: (typed_count(value) if key in TYPED else value) for key, value in group.items()}
    effective = group.get('deal.effective_date') or ''
    out['deal.effective_date'] = date.fromisoformat(effective) if effective else ''
    out['group.fte'] = fte_count
    out['rfp.funding_token'] = uhc_funding(funding)
    out['rfp.aetna_underwriting'] = aetna_underwriting(funding)
    for key, ours in UHC_QUOTE_LINES.items():
        out[f'rfp.quote.{key}'] = 'Quote' if set(quoted) & set(ours) else 'Do not Quote'
    return out


def facts(deal):
    return from_facts(quote_facts.group_facts(deal), funding_asked(deal), list(deal.requested_lines or []), fte(deal))


def form_facts(ctx):
    """{source: value} the request forms and the cover print (K101), from one request (`context.Request`)."""
    out = from_facts(ctx.group, ctx.funding, ctx.lines, ctx.fte)
    due = ctx.stored['due_date']
    out['deal.due_date'] = date.fromisoformat(due) if due else ''
    out['broker.commission'] = ctx.commission[0]
    out['broker.is_bor'] = True if ctx.group.get('broker.is_bor') else None
    current = ctx.group.get('group.current_funding') or ''
    out['group.current_funding'] = FUNDING_WORDS.get(current, current)
    for key in request.FUNDING_KEYS:
        out[f'funding.{key}'] = True if key in ctx.funding else None
    return out
