"""The Proposal tab's payload (plan.md §7.9, §8.12)."""

from deals import lines
from quotes import selectors as quotes

from . import preview, selection
from .models import ProposalConfig


def proposal_lines(deal, states):
    """Requested lines that have plans, in §4.1 order."""
    return [key for key in lines.LINE_KEYS if key in deal.requested_lines and key in states]


def line_payload(line, state, config):
    plans, data, results, packages, recommendation = state
    columns, is_default = selection.presented_for(state)
    by_id = data.by_id
    labels = {p.id: p.option_label or '—' for p in plans}
    names = {p.id: f'{p.option_label} · {p.name}' if p.option_label else p.name for p in plans}
    unpriced = [p for p in columns if results[p.id]['monthly'] is None]
    return {
        'line': line,
        'label': lines.label(line),
        'plan_ids': [p.id for p in columns],
        'is_default': is_default,
        'recommendation': recommendation,
        'available': [
            {
                'id': p.id,
                'role': p.role,
                'carrier': p.carrier,
                'name': p.name,
                'starred': p.starred,
                'recommended': p.recommended,
                'option_label': p.option_label,
                'base_ids': results[p.id]['base_ids'],
                'annual': results[p.id]['annual'],
                'change': results[p.id]['change'],
                'part_of': results[p.id]['part_of'],
            }
            for p in plans
        ],
        'preview': {
            'columns': [
                {
                    'plan_id': p.id,
                    'option': labels[p.id],
                    'role': p.role,
                    'carrier': p.carrier,
                    'plan': f'{p.name} ({p.plan_number})' if p.plan_number and p.plan_number not in p.name else p.name,
                    'recommended': p.recommended,
                }
                for p in columns
            ],
            'design_rows': preview.design_rows(line, columns),
            'cost_rows': preview.cost_rows(line, columns, results, by_id),
            'packages': preview.package_rows(packages, columns, names),
            'summary': preview.summary(plans, results, packages, recommendation, names, config.reasons.get(line, '')),
        },
        'warnings': (
            [
                f'{lines.label(line)}: {len(unpriced)} plan{"s have" if len(unpriced) != 1 else " has"} '
                'no price — enter enrollment in the Advisor'
            ]
            if unpriced
            else []
        ),
    }


def payload(deal):
    config = ProposalConfig.for_deal(deal)
    states = quotes.deal_state(deal)  # every line in one grouped read (Q.7)
    line_payloads = [line_payload(line, states[line], config) for line in proposal_lines(deal, states)]
    blockers = [
        f'{p["label"]}: Nothing recommended for {", ".join(p["recommendation"]["missing"])}'
        for p in line_payloads
        if not p['recommendation']['covered']
    ]
    return {
        'title': config.title,
        'notes': config.notes,
        'reasons': config.reasons,
        'lines': line_payloads,
        'issues': [],
        'warnings': [w for p in line_payloads for w in p['warnings']],
        'issue_blockers': blockers,
        'can_issue': bool(line_payloads) and not blockers,
    }
