"""The one headcount and its cross-check (plan.md §5.7; K17, K19, M67, O.6 #24, #25; OQ21).

`enrolled_headcount(deal)` → {count, source, estimate, via}: the medical enrollment the Advisor prices with (its
current plans' counts from any source, else the line figure, else the census for the line; employees only, waivers
skipped), else intake's enrolled count, else intake's eligible or total employee count marked as an estimate. The old
app put intake first (OQ21 default: the Advisor first). Every band, checklist tier, printed count, commission basis and
Overview figure calls it; it fills `intake.providers.headcount` (O.1).

`enrollment_check(deal)`: the intake enrolled count, the census medical rollup total and the Advisor's medical
enrollment are three answers to one question; when two or more are known and differ, one warning names all three and
the one the band uses, saying so when that one is an estimate ("Enrolled: intake 42 · census 40 · Advisor 41").
"""

from census import facts as census_facts
from census import rollup
from deals import lines
from deals.models import Deal
from intake import providers as intake_providers

from .state import medical_people

ADVISOR = 'advisor'
WHERE = {
    ADVISOR: 'the Advisor',
    'intake.enrolled_count': 'intake',
    'intake.employee_count': "intake's eligible employees",
    'intake.total_employees': "intake's total employees",
}


def _deal(deal):
    return deal if isinstance(deal, Deal) else Deal.objects.get(pk=deal)


def advisor_count(deal):
    """The Advisor's medical enrolled employees, (count, via) or (None, '')."""
    found = medical_people(deal)
    if not found:
        return None, ''
    figures, via = found
    count = int(sum(figures.get(tier, 0) for tier in lines.TIER_CODES))
    return (count, via) if count else (None, '')


def enrolled_headcount(deal):
    deal = _deal(deal)
    count, via = advisor_count(deal)
    if count:
        return {'count': count, 'source': ADVISOR, 'estimate': False, 'via': via}
    found = intake_providers.DEFAULTS['headcount'](deal.id)  # intake's own answers, the tail of the order
    return {**found, 'via': ''}


def headcount(deal_id):
    """`intake.providers.headcount`: {count, source, estimate}."""
    found = enrolled_headcount(deal_id)
    return {key: found[key] for key in ('count', 'source', 'estimate')}


def _intake_enrolled(deal_id):
    found = intake_providers.DEFAULTS['headcount'](deal_id)
    return found['count'] if found['source'] == 'intake.enrolled_count' else None


def _census_enrolled(deal_id):
    stored = census_facts.stored(deal_id)
    medical = rollup.for_line(stored['rollup'], 'medical')
    return medical['enrolled'] if medical and medical.get('enrolled') else None


def _shown(count):
    return 'none' if count is None else str(count)


def enrollment_check(deal):
    """{intake, census, advisor, used: {count, source, estimate}, differ, warning}."""
    deal = _deal(deal)
    answers = {
        'intake': _intake_enrolled(deal.id),
        'census': _census_enrolled(deal.id),
        'advisor': advisor_count(deal)[0],
    }
    used = headcount(deal.id)
    known = {count for count in answers.values() if count is not None}
    differ = len(known) > 1
    warning = None
    if differ:
        three = ' · '.join(
            f'{name if name != "advisor" else "Advisor"} {_shown(count)}' for name, count in answers.items()
        )
        where = WHERE.get(used['source'], used['source'])
        tail = f' — the band uses {where}, {used["count"]}' + (', an estimate' if used['estimate'] else '')
        warning = f'Enrolled: {three}{tail}.'
    return {**answers, 'used': used, 'differ': differ, 'warning': warning}
