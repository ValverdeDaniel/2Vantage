"""What the client spreadsheet is built from: one client-shaped read of the deal (plan.md §9.4, J.4; old
`presentation_workbook._narrow` and `workbook_inputs` at 891f1b3).

This is the allow-list. The tabs read only what it returns, so nothing a client must never see can reach a cell
whatever else the deal holds (J.4 "never": non-client fields such as `sl_lasers`, `star_reason`, internal notes,
sources and document names, review marks, commission figures, the intake's client guidance, birth dates). A plan
carries its client fields, its identity, its marks and quotes' result for it; a line its settings, its plans in
`order.layout`'s order, the plans the proposal presents (as Pages and Issue lay them out, with the option numbers
Issue would stamp) and the people quotes' math prices it with. Reads only; a fixed number of queries.
"""

import io
from collections import namedtuple
from dataclasses import dataclass, field
from pathlib import Path

from deals import carriers, lines, rules
from deals.models import AgencySettings
from intake import coverage as intent
from intake.selectors import intent_rows_for
from quotes import fields
from quotes import math as m
from rfp.selectors import asked_by_line

from .. import builder, catalog, config, deal_cards, line_block, line_layout, pictures, ready, why
from .. import summary_read as read

UNKNOWN_CARRIER = 'Unknown carrier'
# The agency logo until one is uploaded (old `presentation_styles.LOGO_PATH`, `branding.logo_source` at 891f1b3).
BUNDLED_LOGO = Path(__file__).resolve().parents[2] / 'assets' / 'images' / 'logos' / 'agency-logo.png'
Plan = namedtuple(
    'Plan', 'id role carrier identity name plan_number values recommended sold starred priced result version_of'
)


@dataclass
class Line:
    key: str
    label: str
    rate_basis: str
    field_set: str
    parts: dict
    picked: list  # the design rows the builder keeps, in its order (every client field when it keeps them all)
    picked_all: bool
    table_note: str
    plans: list = field(default_factory=list)  # every quoted plan on the line, in order.layout's order
    presented: list = field(default_factory=list)  # the plans the proposal presents, in that order
    labels: dict = field(default_factory=dict)  # {plan id: 'Current' | priced label | 'Option n' | carrier}
    data: object = None  # quotes' LineData, for its math
    people: dict | None = None  # the line's enrolled people (quotes' `people`), what the Compare counts start from
    people_source: str = ''
    hidden: set = field(default_factory=set)  # carrier identities hidden on Markets checked
    kept: dict | None = None  # a line presented as in force (no plans): its stated facts

    @property
    def composite(self):
        return self.rate_basis == 'composite'

    @property
    def current_ids(self):
        return [plan.id for plan in self.presented if plan.role == 'current']


@dataclass
class Facts:
    client: str
    effective: object
    renewal: bool
    agency: dict
    logo: bytes | None
    title: str
    intro: str
    reasons: dict  # {line: the words `why.why_for` prints under it}
    line_words: bool  # whether any line has words of its own (else the deal-wide words print once)
    summary: dict  # {on, blocks: [client block]}
    markets: dict  # {on, lines: [{key, label, rows: [{carrier, current, quoted, presented, note}]}]}
    output: dict
    lines: list
    draft: str
    banner: bytes | None = None  # the cover's upload as the Cover tab's banner (J145; slice 34, `pictures.banner`)


def _values(plan):
    return {key: value for key, value in (plan.values or {}).items() if fields.BY_KEY.get(key, {}).get('client')}


def _plan(row, data, result):
    plan = data.by_id[row.id]
    root = data.root(plan)
    return Plan(
        id=row.id,
        role=row.role,
        carrier=carriers.display_name(row.carrier) or UNKNOWN_CARRIER,
        identity=carriers.identity(row.carrier) or f'plan:{row.id}',
        name=(row.client_name or row.name or '').strip(),
        plan_number=(row.plan_number or '').strip(),
        values=_values(row),
        recommended=bool(row.recommended),
        sold=bool(row.sold),
        starred=bool(row.starred),
        priced=str((row.derived or {}).get('label') or '').strip() if root.id != plan.id else '',
        result=result,
        version_of=plan.version_of,
    )


def _labels(presented, options):
    """The Package row: Current, a priced version's own label, "Option n", else the carrier's name."""
    out = {}
    for plan in presented:
        if plan.role == 'current':
            out[plan.id] = 'Current'
        elif plan.priced:
            out[plan.id] = plan.priced
        elif options.get(plan.id):
            out[plan.id] = f'Option {options[plan.id]}'
        else:
            out[plan.id] = plan.carrier
    return out


def _line(key, stored, state, laid, hidden):
    vocab = lines.BY_KEY[key]
    spec = config.line_spec(stored, key)
    plans = [_plan(row, state.data, state.results[row.id]) for row in state.plans]
    by_id = {plan.id: plan for plan in plans}
    presented = [by_id[plan.id] for plan in laid.shown]
    picked = spec['rows'] if spec['rows'] is not None else [*catalog.client_keys(key), 'plan_number']
    people = m.people(state.data, state.results) if state.plans else None
    return Line(
        key=key,
        label=vocab['label'],
        rate_basis=vocab['rate_basis'],
        field_set=vocab['field_set'],
        parts=dict(spec['parts']),
        picked=list(picked),
        picked_all=spec['rows'] is None,
        table_note=str(spec['table_note'] or ''),
        plans=plans,
        presented=presented,
        labels=_labels(presented, laid.options),
        data=state.data,
        people=people[0] if people else None,
        people_source=people[1] if people else '',
        hidden=hidden,
    )


def _kept(key, stored, row, effective):
    card = line_block.incumbent(row) or {}
    spec = config.line_spec(stored, key)
    vocab = lines.BY_KEY[key]
    facts = Line(key, vocab['label'], vocab['rate_basis'], vocab['field_set'], dict(spec['parts']), [], True, '')
    facts.kept = {**card, 'effective_date': effective}
    return facts


def logo_png(agency):
    """The agency's logo as a fresh PNG (the pixels re-encoded, no metadata): its upload, else the bundled logo the
    old app used until one was uploaded (J145), or None when neither can be read."""
    try:
        from PIL import Image

        if agency.logo:
            with agency.logo.open('rb') as handle:
                raw = handle.read()
        else:
            raw = BUNDLED_LOGO.read_bytes()
        picture = Image.open(io.BytesIO(raw))
        picture.load()
        out = io.BytesIO()
        picture.convert('RGBA').save(out, format='PNG')
        return out.getvalue()
    except Exception:  # an unreadable or missing file: the Cover prints the agency's name instead
        return None


def _client_markets(found, stored):
    lines_out = []
    for entry in found['lines']:
        rows = [
            {key: row[key] for key in ('carrier', 'current', 'quoted', 'presented', 'note')}
            for row in entry['rows']
            if not row['hidden']
        ]
        lines_out.append({'key': entry['key'], 'label': entry['label'], 'rows': rows})
    return {'on': bool(found['on']), 'lines': lines_out}


def _client_blocks(blocks):
    keys = ('label', 'scope', 'line', 'line_label', 'available', 'value_label', 'sub', 'delta_label')
    return [{key: block.get(key) for key in keys} for block in blocks if block.get('available')]


def read_deal(deal):
    """The deal's `Facts`."""
    stored = line_layout.stored_config(deal)
    keys, line_states, off, states = builder.proposal_lines(deal)
    keys = config.ordered(stored, [key for key in keys if key not in off])
    tops = line_layout.tops(deal, keys)
    layout = line_layout.layout_of(stored)
    intent_rows = {row['line']: row for row in intent_rows_for(deal.id)}
    agency = AgencySettings.get()
    entries, out_lines = [], []
    for key in keys:
        if key not in states:
            if line_states.get(key) == intent.PRESENTED:
                out_lines.append(_kept(key, stored, intent_rows.get(key), deal.effective_date))
            continue
        state = states[key]
        laid = line_layout.lay_out(state, None, layout, tops.get(key, 0))
        hidden = set(config.get(stored, f'markets.lines.{key}.hidden') or ())
        out_lines.append(_line(key, stored, state, laid, hidden))
        entries.append((key, state, laid, line_states.get(key, ''), intent_rows.get(key)))
    new_business = rules.deal_type(deal) == rules.NEW_BUSINESS
    on = [entry[0] for entry in entries]
    cards = deal_cards.cards(
        stored,
        entries,
        asked=asked_by_line(deal),
        ages=read.ages(deal) if 'medical' in on else None,
        renewal_offer=read.renewal_offer(deal),
        new_business=new_business,
        ready_ok=False,
    )
    by_line = (stored.get('reasons') or {}) if isinstance(stored, dict) else {}
    return Facts(
        client=deal.client.name,
        effective=deal.effective_date,
        renewal=not new_business,
        agency={
            'name': (agency.name or '').strip(),
            'producer': rules.agent_name(deal, agency),
            'phone': (agency.phone or '').strip(),
            'email': (agency.email or '').strip(),
            'address': (agency.address or '').strip(),
            'city_state_zip': (agency.city_state_zip or '').strip(),
        },
        logo=logo_png(agency),
        title=str(config.get(stored, 'title') or '').strip(),
        intro=str(config.get(stored, 'intro') or ''),
        reasons={line.key: why.why_for(stored, line.key) for line in out_lines},
        line_words=any(str(text or '').strip() for text in by_line.values()),
        summary={'on': bool(cards['summary']['on']), 'blocks': _client_blocks(cards['summary']['blocks'])},
        markets=_client_markets(cards['markets'], stored),
        output=config.output(stored),
        lines=out_lines,
        draft=ready.DRAFT_MARK,
        banner=pictures.banner(stored),
    )
