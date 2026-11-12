"""Tab 1 of the stop-loss workbook, In-Force Snapshot (plan.md §9.13; J166, F99; the old `_sl_snapshot_sheet` at
891f1b3): the current contract as a calculator rather than a printout. The census (enrolled employees × months) is
always written, because Option Comparison links its basis here; with no in-force contract the sheet says how to mark
one and stops.

Sections A (premiums), B (aggregate attachment), C (lasers, listed by position: OQ104) and D (the cost framework,
whose MAXIMUM ANNUAL LIABILITY includes the laser add-on). Each formula's stored result is quotes' exact figure
(`math.stop_loss`); the PEPM, monthly and annual mirrors are its `times`, `per_month` and `per_employee`.
"""

from quotes.math import stop_loss as sl

from . import stop_loss_look as look

SPEC_NOTE = 'Not quoted yet — every total below stays blank until this is entered.'
ZERO_NOTE = 'Blank counts as $0.'


def _mirror(sheet, row, rows, pepm, ctx):
    """The PEPM → monthly → annual mirror of one rate row (the old `_sl_pepm_row`; its 0-headcount arms are the old
    sheet's own guard against printing $0 where nobody is counted)."""
    hc, mo = rows['HC'], rows['MO']
    monthly = sl.times(pepm, ctx['lives']) if ctx['lives'] else None
    look.link(sheet, row, 4, f'=$C${hc}', ctx['lives'] or 0)
    look.formula(sheet, row, 5, f'=IF(OR(C{row}="",$C${hc}=0),"",C{row}*D{row})', monthly)
    look.link(sheet, row, 6, f'=$C${mo}', ctx['months'])
    look.formula(sheet, row, 7, f'=IF(OR(E{row}="",$C${mo}=0),"",E{row}*F{row})', sl.times(monthly, ctx['months']))


def _annual_row(sheet, row, rows, template, annual, ctx, bold=False):
    """A section-D row whose ANNUAL figure is authoritative and whose monthly and PEPM derive back from it."""
    hc, mo = rows['HC'], rows['MO']
    look.formula(sheet, row, 7, template, annual, bold=bold)
    look.link(sheet, row, 4, f'=$C${hc}', ctx['lives'] or 0)
    look.link(sheet, row, 6, f'=$C${mo}', ctx['months'])
    look.formula(sheet, row, 5, f'=IF(OR(G{row}="",F{row}=0),"",G{row}/F{row})', sl.per_month(annual, ctx['months']))
    look.formula(
        sheet,
        row,
        3,
        f'=IF(OR(G{row}="",$C${hc}=0,$C${mo}=0),"",G{row}/$C${hc}/$C${mo})',
        sl.per_employee(annual, ctx['lives'], ctx['months']),
        cents=True,
    )


def _terms(sheet, rows, plan):
    terms = plan['terms']
    for key, label, value in (
        ('CARRIER', 'Stop-loss carrier (in force)', plan['carrier']),
        ('PLAN', 'Plan / program', plan['name']),
        ('TPA', 'TPA', terms['tpa_name']),
        ('TPA_GUAR', 'TPA rate guarantee', terms['tpa_rate_guarantee']),
        ('BASIS', 'Contract basis (incurred/paid)', terms['sl_contract_basis']),
        ('RUNIN', 'Run-in period (months)', terms['sl_run_in_months']),
        ('RUNIN_LIM', 'Run-in dollar limit', terms['sl_run_in_limit']),
        ('RUNOUT', 'Run-out / paid window (months)', terms['sl_run_out_months']),
        ('TLO', 'TLO in force?', terms['sl_tlo']),
        ('COLLATERAL', 'Collateral / captive fees (annual)', terms['sl_collateral']),
    ):
        look.put(sheet, rows[key], 2, label, look.BOLD)
        look.text(sheet, rows[key], 3, value)
    look.put(
        sheet,
        rows['COLLATERAL'],
        look.NOTE_COL,
        'Not stop-loss; shown for completeness and excluded from maximum annual liability, as in the hand-built '
        'original.',
        look.NOTE,
    )


def _premiums(sheet, rows, figures, ctx):
    look.section(sheet, rows['BAND_A'], 'A.  IN-FORCE STOP-LOSS PREMIUMS  (fixed cost)', span=7)
    look.headings(sheet, rows['HEAD_A'], ('Line item', 'PEPM rate', 'Headcount', 'Monthly total', 'Months',
                                         'Annual total', 'Notes'))  # fmt: skip
    for key, label, figure, note in (
        ('SPEC', 'Specific stop-loss premium', figures['spec_rate'], SPEC_NOTE),
        ('AGG', 'Aggregate stop-loss premium', figures['agg_rate'], ZERO_NOTE),
        ('LOAD', 'TLO / other SL load', figures['other_load'], ZERO_NOTE),
    ):
        look.put(sheet, rows[key], 2, label)
        look.input_cell(sheet, rows[key], 3, figure, cents=True, note=None if figure is not None else note)
        _mirror(sheet, rows[key], rows, figure, ctx)
    spec, agg, load, prem = rows['SPEC'], rows['AGG'], rows['LOAD'], rows['PREM']
    look.put(sheet, prem, 2, 'Total in-force stop-loss premium', look.BOLD)
    look.formula(sheet, prem, 3, f'=IF(C{spec}="","",C{spec}+N(C{agg})+N(C{load}))', figures['premium_pepm'],
                 cents=True, bold=True)  # fmt: skip
    _mirror(sheet, prem, rows, figures['premium_pepm'], ctx)


def _attachment(sheet, rows, figures, ctx):
    look.section(sheet, rows['BAND_B'], 'B.  IN-FORCE AGGREGATE ATTACHMENT', span=7)
    factor, corridor, att, floor, final = (rows[k] for k in ('FACTOR', 'CORRIDOR', 'ATT_PEPM', 'FLOOR', 'ATT_FINAL'))
    look.put(sheet, rows['SPEC_DED'], 2, 'Specific deductible (per person)')
    look.input_cell(sheet, rows['SPEC_DED'], 3, figures['spec_deductible'],
                    note='Baseline for every non-lasered claimant.')  # fmt: skip
    look.put(sheet, factor, 2, 'Expected claims factor PEPM')
    look.input_cell(sheet, factor, 3, figures['factor_pepm'], cents=True,
                    note='Underwriter expected claims PEPM, before the corridor.')  # fmt: skip
    _mirror(sheet, factor, rows, figures['factor_pepm'], ctx)
    look.put(sheet, corridor, 2, 'Aggregate corridor')
    look.input_cell(sheet, corridor, 3, figures['corridor'], cents=True)
    look.put(sheet, att, 2, 'Aggregate attachment PEPM')
    look.formula(sheet, att, 3, f'=IF(OR(C{factor}="",C{corridor}=""),"",C{factor}*C{corridor})',
                 figures['attachment_pepm'], cents=True)  # fmt: skip
    _mirror(sheet, att, rows, figures['attachment_pepm'], ctx)
    look.put(sheet, floor, 2, 'Minimum annual aggregate deductible (floor)')
    # 0, not blank: the math applies a floor only when it is above 0, so a 0 here is provably not a made-up figure.
    look.input_cell(
        sheet, floor, 3, figures['attachment_floor'] or 0, note='0 = the attachment floats with the census.'
    )
    look.put(sheet, final, 2, 'Final annual aggregate attachment', look.BOLD)
    _annual_row(sheet, final, rows, f'=IF(G{att}="","",IF(C{floor}=0,G{att},MAX(G{att},C{floor})))',
                figures['annual_attachment'], ctx, bold=True)  # fmt: skip


def _lasers(sheet, rows, plan, figures):
    look.section(sheet, rows['BAND_C'], 'C.  IN-FORCE LASERS  (additional liability = laser − spec, floored at $0)',
                 span=7)  # fmt: skip
    look.headings(sheet, rows['HEAD_C'], ('Laser', 'Laser amount', 'Spec deductible', 'Additional liability',
                                         'Lasers above spec'))  # fmt: skip
    spec_row, spec = rows['SPEC_DED'], figures['spec_deductible']
    first, last, total = rows['LASER_FIRST'], rows['LASER_LAST'], rows['LASER_TOT']
    for n, row in enumerate(range(first, last + 1), start=1):
        amount = plan['lasers'][n - 1] if n <= len(plan['lasers']) else None
        if amount is not None:
            look.text(sheet, row, 2, look.laser_label(n))
        look.input_cell(sheet, row, 3, amount)
        look.link(sheet, row, 4, f'=$C${spec_row}', spec or 0)
        extra = sl.above_spec(amount, spec)
        look.formula(sheet, row, 5, f'=IF(C{row}="","",IF($C${spec_row}="","",MAX(0,C{row}-D{row})))', extra)
    if not plan['lasers']:
        look.put(sheet, first, look.NOTE_COL, 'No lasers recorded. Type a laser amount here and the maximum annual '
                 'liability below re-rates.', look.NOTE)  # fmt: skip
    look.put(sheet, total, 2, 'Total additional laser liability', look.BOLD)
    look.formula(sheet, total, 3, f'=SUM(C{first}:C{last})', sl.total(plan['lasers']))
    guard = f'AND(COUNT(C{first}:C{last})>0,$C${spec_row}="")'
    look.formula(sheet, total, 5, f'=IF({guard},"",SUM(E{first}:E{last}))', figures['laser_liability'], bold=True)
    above = '+'.join(f'IF(N(E{row})>0,1,0)' for row in range(first, last + 1))
    look.formula(sheet, total, 6, f'=IF({guard},"",{above})', figures['laser_count'])
    look.put(sheet, total, look.NOTE_COL, 'Blank (not $0) when lasers exist but the specific deductible does not — the '
             'subtraction would be a guess.', look.NOTE)  # fmt: skip


def _framework(sheet, rows, figures, ctx):
    look.section(sheet, rows['BAND_D'], 'D.  IN-FORCE COST FRAMEWORK  (max liability includes laser add-on)', span=7)
    look.headings(sheet, rows['HEAD_D'], ('Expense', 'PEPM', 'Headcount', 'Monthly', 'Months', 'Annual', 'Notes'))
    hc, mo, admin = rows['HC'], rows['MO'], rows['ADMIN']
    look.put(sheet, admin, 2, 'Administration / TPA / network PEPM')
    look.input_cell(
        sheet,
        admin,
        3,
        figures['admin_pepm'],
        cents=True,
        note='Not stop-loss; included so the maximum cost is complete. Optional — blank counts as $0.',
    )
    look.link(sheet, admin, 4, f'=$C${hc}', ctx['lives'] or 0)
    look.link(sheet, admin, 6, f'=$C${mo}', ctx['months'])
    monthly_admin = sl.times(figures['admin_pepm'] or 0, ctx['lives'] or 0)
    look.formula(sheet, admin, 5, f'=N(C{admin})*D{admin}', monthly_admin)
    look.formula(sheet, admin, 7, f'=E{admin}*F{admin}', figures['annual_admin'])
    prem, factor, final, lasers = (
        f'G{rows["PREM"]}',
        f'G{rows["FACTOR"]}',
        f'G{rows["ATT_FINAL"]}',
        f'E{rows["LASER_TOT"]}',
    )
    g_admin = f'G{admin}'
    for key, label, template, annual, bold in (
        ('FIXED', 'Total fixed cost (SL premium + admin)', f'=IF({prem}="","",{prem}+{g_admin})',
         figures['fixed_cost'], False),
        ('EXPECTED', 'Expected claims (factor × HC × months)', f'=IF({factor}="","",{factor})',
         figures['annual_expected_claims'], False),
        ('PROJECTED', 'Projected plan cost (fixed + expected claims)',
         f'=IF(OR({prem}="",{factor}=""),"",{prem}+{g_admin}+{factor})', figures['projected_cost'], False),
        ('ATTACH', 'Annual aggregate attachment', f'=IF({final}="","",{final})', figures['annual_attachment'], False),
        ('LASERS', 'Additional laser liability (from Section C)', f'=IF({lasers}="","",{lasers})',
         figures['laser_liability'], False),
        ('MAL', 'MAXIMUM ANNUAL LIABILITY  (SL + admin + attachment + lasers)',
         f'=IF(OR({prem}="",{final}="",{lasers}=""),"",{prem}+{g_admin}+{final}+{lasers})',
         figures['max_annual_liability'], True),
    ):  # fmt: skip
        look.put(sheet, rows[key], 2, label, look.NAVY_BOLD if bold else None)
        _annual_row(sheet, rows[key], rows, template, annual, ctx, bold=bold)
    look.put(sheet, rows['NOTE'], 2, 'Change the headcount, a PEPM rate, the corridor or a laser amount and every '
             'total on both analysis tabs re-rates.')  # fmt: skip


def write(sheet, ctx):
    """Tab 1. `ctx`: the workbook's facts (`stop_loss_build.Facts` as a dict) with `rows`, this tab's geometry."""
    rows, current = ctx['snapshot_rows'], ctx['current']
    sheet.zoom = look.ZOOM
    look.widths(sheet, (('B', 46), ('C', 16), ('D', 12), ('E', 16), ('F', 10), ('G', 18), ('H', 44)))
    look.title(sheet, f'IN-FORCE STOP-LOSS — CURRENT CONTRACT SNAPSHOT · {ctx["client"]}')
    look.put(sheet, 2, 2, look.ROUNDTRIP_NOTE, look.WRAP)
    look.put(sheet, rows['HC'], 2, 'Enrolled employees (headcount)', look.BOLD)
    look.input_cell(sheet, rows['HC'], 3, ctx['lives'], note='PEPM math uses EMPLOYEES, never members.')
    look.put(sheet, rows['MO'], 2, 'Months in contract', look.BOLD)
    look.input_cell(sheet, rows['MO'], 3, ctx['months'])
    if current is None:
        look.put(sheet, rows['CARRIER'], 2, 'No in-force stop-loss contract recorded. Mark one plan on the Stop-Loss '
                 'line as the current plan and its terms will fill this sheet.')  # fmt: skip
        return
    figures = current['figures']
    _terms(sheet, rows, current)
    _premiums(sheet, rows, figures, ctx)
    _attachment(sheet, rows, figures, ctx)
    _lasers(sheet, rows, current, figures)
    _framework(sheet, rows, figures, ctx)
    sheet.freeze = (3, 3)
