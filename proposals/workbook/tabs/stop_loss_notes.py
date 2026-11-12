"""Tabs 3–5 of the stop-loss workbook (plan.md §9.13; J166, G117; the old `build_stop_loss_workbook` at 891f1b3):
Binding Notes (the binding and disclosure checklist, live where the deal knows the answer: the SIIA disclosure through
quotes' `disclosure_state` provider), the Glossary, and FIE Rates (the budget in fully-insured-equivalent tier terms:
tier enrollment prefilled from the medical people, the FIE and ER rates left as the producer's inputs, live formulas).
"""

from quotes.math import stop_loss as sl
from quotes.selectors import binding

from . import stop_loss_look as look

GLOSSARY = [
    ('In-force snapshot', 'The current contract. All incoming proposals are measured against this page.'),
    ('Headcount (EE)', 'Enrolled employees. PEPM math uses employees, not members.'),
    ('PEPM', 'Per employee per month. Annual = PEPM x headcount x months.'),
    ('Specific deductible', 'Per-person amount the plan retains before specific stop-loss reimburses.'),
    ('Laser', 'A higher individual deductible assigned to a known claimant. Carrier-specific.'),
    ('Additional laser liability', 'Laser amount minus specific deductible (floored at $0). Extra dollars the employer '
     'keeps on that person.'),
    ('Total laser liability', 'Sum of additional laser liability for every included laser, plus any new claimant a '
     'proposal lasers.'),
    ('Aggregate attachment', 'Plan-wide claims cap. Annual = factor PEPM x corridor x headcount x months (or the '
     'quoted minimum floor).'),
    ('Maximum annual liability', 'Annual SL premium + annual admin + annual aggregate attachment + total additional '
     'laser liability.'),
    ('Run-in period', 'Months before the effective date whose incurred claims can still be covered (common on 15/12 '
     'first-year contracts).'),
    ('Run-in dollar limit', 'Optional cap on how much run-in the carrier will accept. 0 = no separate dollar cap '
     'quoted.'),
    ('Run-out / paid window', 'How long after year-end a claim can be paid and still count (12/15 = 3 extra paid '
     'months).'),
    ('TLO', 'Terminal liability option — extra paid window if the policy is not renewed.'),
    ('Contract basis', 'Incurred months / paid months (12/12, 12/15, 15/12, etc.).'),
]  # fmt: skip
TIERS = (('Employee Only', 'EE'), ('Employee + Spouse', 'ES'), ('Employee + Child(ren)', 'EC'), ('Family', 'FAM'))
FIE_HEADINGS = ('Rates', 'Enrolled', 'FIE', 'ER', 'EE', 'Total Budget', 'Annual ER', 'Annual EE')


def write_binding(sheet, ctx):
    """Tab 3: each item and its live status, then the footer."""
    sheet.zoom = look.ZOOM
    look.widths(sheet, (('B', 58), ('C', 44)))
    look.title(sheet, 'BINDING & DISCLOSURE NOTES')
    look.put(sheet, 2, 2, 'Working paper. Statuses below are live from the deal where the system knows them.')
    look.put(sheet, 4, 2, 'Item', look.BOLD)
    look.put(sheet, 4, 3, 'Status / note', look.BOLD)
    row = 5
    for item, status in ctx['binding']:
        look.put(sheet, row, 2, item)
        look.put(sheet, row, 3, status)
        row += 1
    look.put(sheet, row + 1, 2, binding.FOOTER, look.WRAP)


def write_glossary(sheet, ctx):
    """Tab 4: the terms the workbook uses, in its own words."""
    sheet.zoom = look.ZOOM
    look.widths(sheet, (('B', 30), ('C', 100)))
    look.title(sheet, 'TERMS USED IN THIS WORKBOOK')
    look.put(sheet, 3, 2, 'Term', look.BOLD)
    look.put(sheet, 3, 3, 'Meaning here', look.BOLD)
    for row, (term, meaning) in enumerate(GLOSSARY, start=4):
        look.put(sheet, row, 2, term)
        look.put(sheet, row, 3, meaning)


def write_fie(sheet, ctx):
    """Tab 5: fully-insured-equivalent rates. The FIE and ER cells are judgment, left for the producer; with them
    blank every budget figure is 0, as the formulas read it."""
    sheet.zoom = look.ZOOM
    look.widths(sheet, [('A', 24)] + [(letter, 14) for letter in 'BCDEFGH'])
    look.put(sheet, 1, 1, 'Fully Insured Equivalent Rates', look.TITLE)
    look.headings(sheet, 2, FIE_HEADINGS, start=1)
    zero = sl.times(0)
    for row, (label, tier) in enumerate(TIERS, start=3):
        look.put(sheet, row, 1, label)
        look.put(sheet, row, 2, look.number(ctx['tiers'].get(tier)) or 0)
        look.link(sheet, row, 5, f'=C{row}-D{row}', zero)
        look.link(sheet, row, 6, f'=C{row}*B{row}*12', zero)
        look.link(sheet, row, 7, f'=D{row}*B{row}*12', zero)
        look.link(sheet, row, 8, f'=E{row}*B{row}*12', zero)
    look.put(sheet, 7, 1, 'Total Annual Budget', look.BOLD)
    look.put(sheet, 8, 1, 'Monthly Claim Budget')
    for col, letter in ((6, 'F'), (7, 'G'), (8, 'H')):
        look.link(sheet, 7, col, f'=SUM({letter}3:{letter}6)', zero)
        look.link(sheet, 8, col, f'={letter}7/12', zero)
    look.put(sheet, 10, 1, 'FIE and ER rates are inputs — set them, then play with the split.')
