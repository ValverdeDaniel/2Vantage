"""Our census values in each carrier's own words (plan.md §9.8 "Cells"; K92). Pure. Ported from old Vantage 891f1b3
`benefits/pipeline/plan_math.py` (the vocabulary layer of 2026-09-17).

Each translated column goes in two steps: our value becomes a CANONICAL token here (tier `EE/ES/EC/FAM/WAIVE`, gender
`M/F`, status `ACTIVE/COBRA/STCON/RETIREE`, relationship `employee/spouse/child/domestic_partner`, `ENROLL`), then the
format's own `value_map` spells it the carrier's way. A token missing from the map writes blank, never a guess (D-144);
a token mapped to '' is blank on purpose (UHC leaves the employee's own relationship empty).

`typed(column, text)` is the value a workbook cell gets for one shown string: a `date` column a real date, a `zip5` a
number unless it starts with a zero, a salary, volume or derived age a number. Whether the target cell then stores a
number or the text of one is the filler's call, from the cell's own number format (`rfp.xlsx.sheet`).
"""

import re

from census import fields
from census.importer.words import is_waiver, tier_code
from census.values import parse_date

SPOUSE_WORDS = ('spouse', 'wife', 'husband', 'partner', 'dp', 'sp')
CHILD_WORDS = ('child', 'son', 'daughter', 'dependent', 'stepchild', 'ch')
DP_WORDS = ('domestic', 'dp', 'civil union')

# Census keys a carrier's cell expects as a NUMBER: a person typing 61500 into Warner's "$"#,##0 salary cell leaves a
# number, so we do too. A derived age has no census key, so its source is listed.
NUMERIC_FIELDS = frozenset(
    {'annual_salary', 'hours_per_week', 'vol_life_amount', 'basic_life_amount', 'std_amount', 'ltd_amount'}
)
NUMERIC_SOURCES = frozenset({'derive:age'})
TOKENS = ('tier', 'gender', 'status')

# What a canonical token reads as in a translation note (D-143). The note names the token, never a person.
TOKEN_WORDS = {
    'WAIVE': 'waived',
    'RETIREE': 'retired',
    'COBRA': 'on COBRA',
    'STCON': 'on state continuation',
    'domestic_partner': 'a domestic partner',
    'spouse': 'a spouse',
    'child': 'a child',
    'ACTIVE': 'active',
}


def tier(raw):
    """EE / ES / EC / FAM, WAIVE for an explicit decline, or ''."""
    text = str(raw or '').strip()
    if not text:
        return ''
    if is_waiver(text) or text == fields.WAIVED:
        return 'WAIVE'
    return tier_code(text)


def gender(raw):
    text = str(raw or '').strip().upper()
    if text.startswith('M'):
        return 'M'
    if text.startswith('F'):
        return 'F'
    return ''


def status(raw):
    """ACTIVE / COBRA / STCON / RETIREE. Our employment status is free text and usually says Full-time or Part-time,
    which does not answer the carrier's question (COBRA and continuation), so anything that is not explicitly a
    continuation reads ACTIVE (Daniel, 2026-09-17), and the format's gaps say so."""
    text = str(raw or '').strip().upper()
    if 'COBRA' in text:
        return 'COBRA'
    if 'RETIRE' in text:
        return 'RETIREE'
    if 'ST CON' in text or 'CONTINU' in text:
        return 'STCON'
    return 'ACTIVE'


def relationship(kind, raw):
    """employee / domestic_partner / child / spouse: an employee row is the employee; a dependent's free-text
    relationship refines which kind, and one nobody filled in (or nobody can read) is a child, said in a note."""
    if kind == fields.EMPLOYEE:
        return 'employee'
    text = str(raw or '').strip().lower()
    if any(word in text for word in DP_WORDS):
        return 'domestic_partner'
    if any(word in text for word in CHILD_WORDS):
        return 'child'
    if any(word in text for word in SPOUSE_WORDS):
        return 'spouse'
    return 'child'


def relationship_is_default(kind, raw):
    """Would `relationship` fall back to a child for this dependent? The file says so rather than letting the guess
    pass as a fact (D-143)."""
    if kind == fields.EMPLOYEE:
        return False
    text = str(raw or '').strip().lower()
    return not any(word in text for word in DP_WORDS + CHILD_WORDS + SPOUSE_WORDS)


def canonical(column, raw):
    """(token or value, whether the column's value_map applies)."""
    transform = column.get('transform') or ''
    if transform == 'tier':
        return tier(raw), True
    if transform == 'gender':
        return gender(raw), True
    if transform == 'status':
        return status(raw), True
    return raw, False


def shaped(value, transform):
    """A value with no token after its transform, as the preview shows it (MM/DD/YYYY dates, 5-digit ZIPs)."""
    text = str(value or '').strip()
    if not text:
        return ''
    if transform == 'date':
        parsed = parse_date(text)
        return parsed.strftime('%m/%d/%Y') if parsed else text
    if transform == 'zip5':
        # A ZIP+4 loses its suffix; a four-digit value gets back the leading zero a spreadsheet dropped.
        digits = re.sub(r'\D', '', text)
        if len(digits) == 4:
            return '0' + digits
        if 5 <= len(digits) <= 9:
            return digits[:5]
        return text
    if transform == 'initial':
        return text[:1].upper()
    return text


def _number(text):
    cleaned = str(text or '').strip().replace('$', '').replace(',', '')
    if not re.fullmatch(r'-?\d+(\.\d+)?', cleaned):
        return None
    return float(cleaned) if '.' in cleaned else int(cleaned)


def typed(column, text):
    """The value a workbook cell gets for one shown string ('' writes nothing)."""
    text = '' if text is None else str(text)
    if not text.strip():
        return ''
    transform = column.get('transform') or ''
    if transform == 'date':
        return parse_date(text) or text
    if transform == 'zip5':
        digits = text.strip()
        return int(digits) if digits.isdigit() and not digits.startswith('0') else text
    if (column.get('field') or '') in NUMERIC_FIELDS or (column.get('source') or '') in NUMERIC_SOURCES:
        number = _number(text)
        return text if number is None else number
    return text


def column_required(column):
    """Is this column required by the carrier? THE one rule (D-143): our `required` flag, or the carrier's asterisk on
    its own header (UHC prints `*Gender`, Angle `Zip*`). The rows' missing cells, the lens, the Census tab's required
    cells and the check all read it."""
    if column.get('required'):
        return True
    text = (column.get('header') or '').strip()
    return text.startswith('*') or text.endswith('*')


def _plural(n, one, many):
    return one if n == 1 else many


def note_text(code, count, header='', token=''):
    """The count-only sentence a translation note puts in a file's warnings: never a name or a value."""
    if code == 'no_carrier_code':
        word = TOKEN_WORDS.get(token, f'"{token}"')
        return (
            f'{count} {_plural(count, "member is", "members are")} {word} on "{header}" — this format has no code '
            f'for that, so {_plural(count, "it goes", "they go")} out blank.'
        )
    if code == 'terminated_active':
        return (
            f'{count} {_plural(count, "employee is", "employees are")} marked terminated but '
            f'{_plural(count, "goes", "go")} out as Active — remove them or mark COBRA.'
        )
    if code == 'relationship_default':
        return (
            f'{count} {_plural(count, "dependent has", "dependents have")} no relationship on file and '
            f'{_plural(count, "goes", "go")} out as a child.'
        )
    if code == 'unparsed':
        return (
            f'{count} {_plural(count, "member has", "members have")} a "{header}" we cannot read — '
            f'{_plural(count, "it goes", "they go")} out blank.'
        )
    return ''
