"""What every line tab of the client spreadsheet shares (plan.md §9.4; old `presentation_workbook` at 891f1b3): the
subtitle and dates, the plan's printed name, the SOLD / RECOMMENDED marker, the notes under a table, and the old words.
"""

import datetime

from .. import cells, layout
from .. import print_plan as pp
from .. import styles as s

TIER_LABEL = {
    'EE': 'Employee Only',
    'ES': 'Employee + Spouse',
    'EC': 'Employee + Child(ren)',
    'FAM': 'Employee + Family',
}
DISCLAIMER = (
    '*Disclaimer: Premiums may change based on final enrollment participation. '
    'Rates as quoted, subject to final underwriting.'
)
PCT_NOTE = 'Percentage from current is shown when a line has a single current plan.'
TYPED_PLAN_NOTE = 'Some plans use expected enrollment entered for that plan.'
# Where the current plan's counts came from (quotes' enrollment sources), in the old note's words.
ENROLL_NOTE = {
    'census': 'Enrolled counts from the census.',
    'line': 'Enrolled counts typed for the whole line.',
    'proxy': 'Enrolled counts borrowed from medical (this line has no tier column).',
    'medical': 'Enrolled counts from medical enrollment.',
    'typed': 'Enrolled counts typed for this plan.',
    'from original plan': "Enrolled counts typed for this plan's original.",
    'from current plan': 'Enrolled counts typed for the current plan this renews.',
    'from replaced plan': 'Enrolled counts typed for the plan it replaces.',
    'none': 'Totals appear once enrollment counts are entered for the current plan.',
}
SEVERAL_CURRENT = "Enter each current plan's enrollment"
NO_CURRENT = "Enter each plan's enrollment"
_MONTHS = (
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
)


def long_date(value):
    """'October 1st, 2026' from a date, a datetime or an ISO date string; '' for anything else."""
    if isinstance(value, datetime.datetime):
        value = value.date()
    if isinstance(value, str):
        try:
            value = datetime.date.fromisoformat(value.strip()[:10])
        except ValueError:
            return ''
    if not isinstance(value, datetime.date):
        return ''
    day = value.day
    suffix = 'th' if 10 <= day % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return f'{_MONTHS[value.month - 1]} {day}{suffix}, {value.year}'


def subtitle(facts):
    """Row 2 of a line tab: the client, and the effective date when there is one."""
    effective = long_date(facts.effective)
    return f'{facts.client} · Effective {effective}' if effective else facts.client


def table_note_rows(line):
    """The producer's note under a line's table, one row per line of it; every tab with the line's plans prints it
    first among its notes."""
    return [text for text in (line.table_note or '').split('\n') if text.strip()]


def _squash(text):
    return ''.join(ch for ch in str(text or '').lower() if ch.isalnum())


def plan_label(plan, picked):
    """The Plan row: the plan's name, its plan number in brackets only when the plan-number row is kept, the plan has
    one, and the name does not already carry it."""
    name = plan.name
    if 'plan_number' in picked and plan.plan_number and _squash(plan.plan_number) not in _squash(name):
        return f'{name} ({plan.plan_number})' if name else plan.plan_number
    return name


def marker(line, plan):
    """The word above a plan and its font: SOLD (it wins), else RECOMMENDED unless the recommendation part is off."""
    if plan.sold:
        return 'SOLD', s.SOLD
    if line.parts.get('recommendation', True) is not False and plan.recommended:
        return 'RECOMMENDED', s.RECOMMENDED
    return '', None


def note_chars(pairs):
    """Characters a line of a note merged across the label column and `pairs` plan pairs holds (322 px for A and
    210 px a pair, about 8 px a character)."""
    return (round(pp.A_IN * 96) + round(pp.PAIR_IN * 96) * pairs) // 8


def notes(sheet, first, last_col, rows, per_line):
    """Note rows from `first` (a spacer above), each merged across 1..last_col; `rows` is [(text, font)]."""
    cells.spacer(sheet, first - 1)
    for row, (text, look) in enumerate(rows, first):
        cells.text(sheet, row, 1, text, font=look, align=s.LEFT)
        if last_col > 1:
            cells.merge_pair(sheet, row, 1, last_col)
        sheet.heights[row] = cells.row_height([(text, per_line)])


part = layout.part


def label(sheet, row, text, *, bold=False, indent=1, border=s.THIN):
    """A row label in column A on white."""
    cells.text(
        sheet,
        row,
        1,
        text,
        font=s.BOLD if bold else s.BODY,
        fill=s.FILL_WHITE,
        border=border,
        align=s.label_align(indent),
    )
