"""The client deck's Facts: one client-shaped read of a deal (plan.md §9.5; J.4, J.6.3; old Vantage 891f1b3
`proposal_payload` with `presentation_content.with_content`). The story reads only what this returns.

Reads, in a fixed number of queries whatever the plan count: the builder's lines (`builder.proposal_lines`: quotes'
`deal_state`, the intent), each line laid out as Pages and Issue lay it out (`line_layout`), the config row, the
deal cards' summary and Markets checked (`deal_cards`), the agency settings, the firm's pages and team. Pictures
and photos travel as bytes in `sources`, never as paths (J.5 B12). Firm pages print nothing until written (OQ41):
blank About, figures, calendar and team stay blank here.

{client, title, kind, year, renewal, effective, prepared_on, prepared_by, draft, version, agency {name, phone,
 email, brand, logo}, intro, recommendation, pages {agenda, about, team, experience, calendar, bios}, layout,
 package_summary, firm {about, stats, calendar}, team [{id, name, title, group, phone, email, bio, photo}],
 experience {summary, rows [{period, premium, claims, ratio}]}, next_steps, pictures {cover, agenda, sections,
 closing}, summary {on, blocks}, markets {on, lines}, glance_facts (the summary's line facts), lines [line Facts],
 kept [kept line], sources {src: bytes}}
"""

from deals import clock, rules
from deals import lines as vocab
from deals.models import AgencySettings
from intake import coverage as intent
from intake.selectors import intent_rows_for
from quotes import math as m
from quotes.selectors.state import empty
from rfp.selectors import asked_by_line

from .. import builder, catalog, config, deal_cards, line_block, line_layout, ready
from .. import summary_read as read
from . import firm_read, line_facts

LOGO = 'logo:agency'


def experience(stored):
    """Typed totals and the producer's summary (Daniel, 2026-11-02): no claimant, no diagnosis. The loss ratio is
    derived on read, only where both figures are typed (J130)."""
    raw = config.experience(stored)
    rows = []
    for row in raw['rows']:
        premium, claims = m.decimal(row.get('premium')), m.decimal(row.get('claims'))
        ratio = m.round_decimal(claims / premium * 100, 1) if premium and claims is not None else None
        rows.append(
            {
                'period': row.get('period') or '',
                'premium': f'${premium:,.0f}' if premium is not None else '—',
                'claims': f'${claims:,.0f}' if claims is not None else '—',
                'ratio': f'{ratio:.1f}%' if ratio is not None else '—',
            }
        )
    return {'summary': (raw['summary'] or '').strip(), 'rows': rows}


def _agency(sources):
    agency = AgencySettings.get()
    logo = firm_read.file_bytes(agency.logo)
    if logo:
        sources[LOGO] = logo
    return agency, {
        'name': agency.name or '',
        'phone': agency.phone or '',
        'email': agency.email or '',
        'brand': agency.brand_color,
        'logo': LOGO if logo else None,
    }


def _lines(deal, stored):
    """(line Facts in the producer's order, kept lines, the summary's entries) for the lines the files print."""
    keys, line_states, off, states = builder.proposal_lines(deal)
    keys = config.ordered(stored, [key for key in keys if key not in off])
    tops = line_layout.tops(deal, keys)
    layout = line_layout.layout_of(stored)
    intent_rows = {row['line']: row for row in intent_rows_for(deal.id)}
    out, kept, entries, sheets = [], [], [], []
    for key in keys:
        state = states.get(key) or empty(key)
        laid = line_layout.lay_out(state, None, layout, tops.get(key, 0))
        row = intent_rows.get(key) or {}
        is_kept = line_states.get(key) == intent.PRESENTED
        incumbent = line_block.incumbent(row if is_kept else None)
        entries.append((key, state, laid, line_states.get(key, ''), intent_rows.get(key)))
        spec = config.line_spec(stored, key)
        ctx = {'config': stored, 'marks': {}, 'state': line_states.get(key, ''), 'off': None, 'spec': spec}
        sheets.append(line_block.facts(key, state, laid, {**ctx, 'incumbent': incumbent}))
        if not laid.shown:
            if is_kept and incumbent:
                kept.append({'key': key, 'label': vocab.label(key), 'incumbent': incumbent})
            continue
        found = {
            'config': stored,
            'spec': spec,
            'intent': line_states.get(key, ''),
            'incumbent': incumbent,
            'guarantee': row.get('rate_guarantee_through'),
        }
        out.append(line_facts.line(key, state, laid, found))
    return out, kept, entries, sheets


def facts(deal):
    stored = line_layout.stored_config(deal)
    sources = {}
    agency_row, agency = _agency(sources)
    found, kept, entries, sheets = _lines(deal, stored)
    gate = ready.ready(sheets)
    cards = deal_cards.cards(
        stored,
        entries,
        asked=asked_by_line(deal),
        ages=read.ages(deal) if any(entry[0] == 'medical' for entry in entries) else None,
        renewal_offer=read.renewal_offer(deal),
        new_business=rules.deal_type(deal) == rules.NEW_BUSINESS,
        ready_ok=gate['ok'],
    )
    effective = deal.effective_date
    year = str(effective.year) if effective else ''
    renewal = rules.deal_type(deal) == rules.RENEWAL
    output = config.output(stored)
    return {
        'client': deal.client.name,
        'title': (config.get(stored, 'title') or '').strip(),
        'kind': f'{year} {"Benefits Renewal" if renewal else "Benefits Proposal"}'.strip(),
        'year': year,
        'renewal': renewal,
        'effective': effective,
        'prepared_on': clock.today(),
        'prepared_by': rules.agent_name(deal, agency_row) or agency['name'],
        'draft': True,  # every file not yet issued carries Draft (OQ35); Issue is slice 32
        'version': None,
        'agency': agency,
        'intro': (config.get(stored, 'intro') or '').strip(),
        'recommendation': (config.get(stored, 'recommendation') or '').strip(),
        'pages': output['pages'],
        'layout': output['layout'],
        'package_summary': output['package_summary'],
        'firm': firm_read.firm(),
        'team': firm_read.team(stored, sources),
        'experience': experience(stored),
        'next_steps': [s for s in config.get(stored, 'next_steps') if (s.get('text') or '').strip()],
        'pictures': catalog.picture_sources(catalog.default_pictures()),
        'summary': {
            'on': cards['summary']['on'],
            'blocks': [block for block in cards['summary']['blocks'] if block.get('available')],
        },
        'markets': cards['markets'],
        'glance_facts': cards['facts']['lines'],
        'lines': found,
        'kept': kept,
        'sources': sources,
    }
