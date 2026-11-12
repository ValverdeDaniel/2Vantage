"""The summary's people blocks for one line: enrollment, who we went to, and the Medicare-eligible count (J64, J66;
old Vantage 891f1b3 `exec_summary._b_enrollment`, `_b_carriers_quoted`, `_b_medicare_eligible`). Pure; (facts, line)
→ body, or `Refused` with the reason.

The 65+ figure is counts only, worked out on the server from the census (§5.3.7): never a name or a birth date.
"""

from deals import lines as line_vocab

from .. import markets
from . import reading as r
from . import words as w

# Where the line's people come from, in the old tile's words.
SOURCE_WORDS = {
    'census': 'from the census',
    'proxy': 'borrowed from the medical tally',
    'medical': 'from medical enrollment',
    'line': 'entered by hand',
    'typed': 'entered by hand',
}


def _line(facts, key):
    return next(line for line in facts['lines'] if line['key'] == key)


def enrollment(facts, key):
    line = _line(facts, key)
    people = line['people']
    figures = (people or {}).get('figures') or {}
    if 'volume' in figures:
        raise r.Refused('This line is priced on volume, not on people')
    total = sum(int(figures[tier]) for tier in figures)
    if not total:
        raise r.Refused(r.NO_ENROLLMENT)
    source = SOURCE_WORDS.get(people['source'], '')
    if 'lives' in figures:
        parts = f'{total} {w.plural(total, "life", "lives")}'
    else:
        parts = ' · '.join(f'{int(figures[tier])} × {tier}' for tier in line_vocab.TIER_CODES if figures.get(tier))
    return {
        'value': total,
        'value_label': f'{total} enrolled',
        'sub': parts + (f' — {source}' if source else ''),
    }


def carriers_quoted(facts, key):
    """Marketing effort, not the document: every quote back on the line counts, starred or not. Once a send names the
    line, it is who we asked: the carriers asked plus any that quoted, the incumbent and the rows hidden from the
    markets table apart, so this figure and that table never disagree."""
    line = _line(facts, key)
    table = markets.line_rows(facts['markets'], key)
    others = [row for row in (table or {}).get('rows') or [] if not row['current']]
    if any(row['asked'] for row in others):
        rows = [row for row in others if not row['hidden']]
        if not rows:
            raise r.Refused('Every carrier on this line is hidden from the markets table')
        quoted = [row for row in rows if row['quoted']]
        if not quoted:
            raise r.Refused('No quotes on this line yet')
        count = len(rows)
        no_quote = [row['carrier'] for row in rows if row['quoted'] is False]
        return {
            'value': count,
            'value_label': f'{count} {w.plural(count, "carrier")} · {len(quoted)} quoted',
            'sub': f'No quote: {", ".join(no_quote)}' if no_quote else 'Every carrier we asked quoted',
        }
    if not line['quotes']:
        raise r.Refused('No quotes on this line yet')
    names = sorted({plan['carrier'] for plan in line['quotes'] if plan['carrier']})
    count, plans = len(names), len(line['quotes'])
    return {
        'value': count,
        'value_label': f'{count} {w.plural(count, "carrier")}',
        'sub': f'{plans} {w.plural(plans, "plan")}' + (f' · {", ".join(names)}' if names else ''),
    }


def medicare_eligible(facts, _key):
    """Members 65 or older at the effective date: the last figure under Medical, a reason to go back to the client
    about Medicare education (the 2026-10-22 call)."""
    ages = facts['ages']
    if not ages or not ages['rows']:
        raise r.Refused('No census on this deal')
    if not ages['with_dob']:
        raise r.Refused('No birth dates on the census')
    if not ages['as_of']:
        raise r.Refused('No effective date to measure ages against')
    employees, dependents = ages['employees_65'], ages['dependents_65']
    count = employees + dependents
    parts = [f'At the {ages["as_of"]} effective date']
    if count:
        parts.append(f'{employees} {w.plural(employees, "employee")}, {dependents} {w.plural(dependents, "dependent")}')
        parts.append('consider Medicare education')
    missing = ages['rows'] - ages['with_dob']
    if missing:
        parts.append(f'{missing} without a birth date')
    return {
        'value': count,
        'value_label': f'{count} {w.plural(count, "member")} 65+' if count else 'No one 65 or older',
        'sub': ' · '.join(parts),
    }
