"""Tab 2 of the stop-loss workbook, Option Comparison (plan.md §9.13; J166, F100–F103; the old `_sl_comparison_sheet`
at 891f1b3): the in-force contract and the incoming options side by side, every figure a formula in the sheet.

The CURRENT column is linked to the In-Force Snapshot. A number linked from it reads `=IF(ref="","",ref)`, so a blank
there stays blank here (a bare link to an empty cell reads 0 and would mint a premium of $0: the old sheet's bare
links; slice 27's Composite fix). Lasers sit on shared numbered rows, each option's own figure on its claimant's row,
never the claimant (OQ104). A column with no specific rate stays blank all the way through, and every delta refuses
when either side is blank. Stored results are quotes' exact figures (`math.stop_loss`).
"""

from . import stop_loss_look as look

PREMIUM_BAND = 'PREMIUMS  (annual = PEPM × headcount × months)'
LASER_BAND = 'LASER LIABILITY   additional = laser − that option’s spec deductible'
LABELS = (
    ('CARRIER', 'Stop-loss carrier'),
    ('TPA', 'TPA'),
    ('BASIS', 'Contract basis (incurred/paid)'),
    ('RUNIN', 'Run-in period (months)'),
    ('RUNIN_LIM', 'Run-in dollar limit'),
    ('RUNOUT', 'Run-out / paid window (months)'),
    ('TLO', 'TLO included / terms'),
    ('SPEC_DED', 'Specific deductible (per person)'),
    ('SPEC_RATE', 'Specific premium PEPM'),
    ('AGG_RATE', 'Aggregate premium PEPM'),
    ('LOAD', 'TLO / other load PEPM'),
    ('PREM_PEPM', 'Total SL premium PEPM'),
    ('PREM_ANN', 'Annual SL premium'),
    ('FACTOR', 'Expected claims factor PEPM'),
    ('CORRIDOR', 'Aggregate corridor'),
    ('FLOOR', 'Min annual agg deductible (floor)'),
    ('ATT_PEPM', 'Attachment PEPM (factor × corridor)'),
    ('ATT_ANN', 'Annual aggregate attachment'),
    ('ADMIN', 'Admin / TPA / network PEPM'),
    ('ADMIN_ANN', 'Annual admin'),
    ('LASER_LIAB', 'Total additional laser liability'),
    ('LASER_CNT', 'Lasers above spec (count)'),
    ('PROJECTED', 'Projected cost (SL + admin + expected claims)'),
    ('VS_MAL', 'Max liability vs CURRENT'),
    ('VS_PREM', 'Annual SL premium vs CURRENT'),
    ('VS_LASER', 'Laser liability vs CURRENT'),
)
# (row, term key, snapshot row) for the text rows; (row, figure, snapshot row, cents) for the inputs.
TEXT_ROWS = (
    ('TPA', 'tpa_name', 'TPA'),
    ('BASIS', 'sl_contract_basis', 'BASIS'),
    ('RUNIN', 'sl_run_in_months', 'RUNIN'),
    ('RUNIN_LIM', 'sl_run_in_limit', 'RUNIN_LIM'),
    ('RUNOUT', 'sl_run_out_months', 'RUNOUT'),
    ('TLO', 'sl_tlo', 'TLO'),
)
INPUT_ROWS = (
    ('SPEC_DED', 'spec_deductible', 'SPEC_DED', False),
    ('SPEC_RATE', 'spec_rate', 'SPEC', True),
    ('AGG_RATE', 'agg_rate', 'AGG', True),
    ('LOAD', 'other_load', 'LOAD', True),
    ('FACTOR', 'factor_pepm', 'FACTOR', True),
    ('CORRIDOR', 'corridor', 'CORRIDOR', True),
    ('ADMIN', 'admin_pepm', 'ADMIN', True),
)


def _shown(value):
    return value if value not in (None, '') else '—'


def _inputs(sheet, rows, snap, col, plan, linked, shared_rows):
    figures, terms = plan['figures'], plan['terms']
    if linked:
        look.link(sheet, rows['CARRIER'], col, f'={look.ref("C" + str(snap["CARRIER"]))}', _shown(plan['carrier']))
    else:
        look.text(sheet, rows['CARRIER'], col, plan['carrier'])
    for row, key, snap_row in TEXT_ROWS:
        if linked:
            look.link(sheet, rows[row], col, f'={look.ref("C" + str(snap[snap_row]))}', _shown(terms[key]))
        else:
            look.text(sheet, rows[row], col, terms[key])
    for row, key, snap_row, cents in INPUT_ROWS:
        if linked:
            source = look.ref('C' + str(snap[snap_row]))
            look.formula(sheet, rows[row], col, f'=IF({source}="","",{source})', figures[key], cents=cents)
        else:
            look.input_cell(sheet, rows[row], col, figures[key], cents=cents)
    floor = figures['attachment_floor'] or 0  # the snapshot's floor is always a number (0 = floats)
    if linked:
        look.formula(sheet, rows['FLOOR'], col, f'={look.ref("C" + str(snap["FLOOR"]))}', floor)
    else:
        look.input_cell(sheet, rows['FLOOR'], col, floor)
    for n in range(1, shared_rows + 1):  # the claimants' rows; the reserve below them stays empty, as the old sheet's
        look.input_cell(sheet, rows['LASER_FIRST'] + n - 1, col, plan['shared'].get(n))


def _formulas(sheet, rows, col, plan):
    figures, c = plan['figures'], look.letter(col)
    hc, mo = f'$C${rows["CENSUS"]}', f'$E${rows["CENSUS"]}'
    r = {key: f'{c}{rows[key]}' for key in rows}
    spec = f'{c}${rows["SPEC_DED"]}'
    lasers = range(rows['LASER_FIRST'], rows['LASER_LAST'] + 1)
    extras = '+'.join(f'MAX(0,N({c}{row})-{spec})' for row in lasers)
    counts = '+'.join(f'IF(MAX(0,N({c}{row})-{spec})>0,1,0)' for row in lasers)
    guard = f'AND(COUNT({c}{rows["LASER_FIRST"]}:{c}{rows["LASER_LAST"]})>0,{spec}="")'
    for key, template, figure, cents, bold in (
        ('PREM_PEPM', f'=IF({r["SPEC_RATE"]}="","",{r["SPEC_RATE"]}+N({r["AGG_RATE"]})+N({r["LOAD"]}))',
         figures['premium_pepm'], True, False),
        ('PREM_ANN', f'=IF(OR({r["PREM_PEPM"]}="",{hc}=0,{mo}=0),"",{r["PREM_PEPM"]}*{hc}*{mo})',
         figures['annual_premium'], False, False),
        ('ATT_PEPM', f'=IF(OR({r["FACTOR"]}="",{r["CORRIDOR"]}=""),"",{r["FACTOR"]}*{r["CORRIDOR"]})',
         figures['attachment_pepm'], True, False),
        ('ATT_ANN', f'=IF(OR({r["ATT_PEPM"]}="",{hc}=0,{mo}=0),"",IF({r["FLOOR"]}=0,{r["ATT_PEPM"]}*{hc}*{mo},'
         f'MAX({r["ATT_PEPM"]}*{hc}*{mo},{r["FLOOR"]})))', figures['annual_attachment'], False, False),
        ('ADMIN_ANN', f'=N({r["ADMIN"]})*{hc}*{mo}', figures['annual_admin'], False, False),
        ('LASER_LIAB', f'=IF({guard},"",{extras})', figures['laser_liability'], False, False),
        ('LASER_CNT', f'=IF({guard},"",{counts})', figures['laser_count'], False, False),
        ('PROJECTED', f'=IF(OR({r["PREM_ANN"]}="",{r["FACTOR"]}="",{hc}=0,{mo}=0),"",'
         f'{r["PREM_ANN"]}+{r["ADMIN_ANN"]}+{r["FACTOR"]}*{hc}*{mo})', figures['projected_cost'], False, False),
        ('MAL', f'=IF(OR({r["PREM_ANN"]}="",{r["ATT_ANN"]}="",{r["LASER_LIAB"]}=""),"",{r["PREM_ANN"]}+'
         f'{r["ADMIN_ANN"]}+{r["ATT_ANN"]}+{r["LASER_LIAB"]})', figures['max_annual_liability'], False, True),
    ):  # fmt: skip
        look.formula(sheet, rows[key], col, template, figure, cents=cents, bold=bold)


def _deltas(sheet, rows, col, plan, first):
    """Against the CURRENT column: none of its own; every other column refuses when either side is blank, and the
    laser delta needs a stated premium too (an unquoted column has laser liability 0)."""
    c, vs = look.letter(col), plan['vs'] or {}
    for row, source, gate, key in (
        ('VS_MAL', 'MAL', '', 'max_annual_liability'),
        ('VS_PREM', 'PREM_ANN', '', 'annual_premium'),
        ('VS_LASER', 'LASER_LIAB', f'{c}{rows["PREM_ANN"]}="",', 'laser_liability'),
    ):
        if first:
            look.put(sheet, rows[row], col, '—', {'align': 'right'})
            continue
        mine, theirs = f'{c}{rows[source]}', f'$C${rows[source]}'
        look.formula(sheet, rows[row], col, f'=IF(OR({gate}{mine}="",{theirs}=""),"",{mine}-{theirs})', vs.get(key))


def write(sheet, ctx):
    """Tab 2. `ctx`: the workbook's facts with this tab's (`option_rows`) and the snapshot's (`snapshot_rows`) rows."""
    rows, snap, current = ctx['option_rows'], ctx['snapshot_rows'], ctx['current']
    columns = ([('CURRENT (in force)', current)] if current else []) + [
        (plan['name'] or plan['carrier'] or f'Option {i}', plan) for i, plan in enumerate(ctx['options'], start=1)
    ]
    sheet.zoom = look.ZOOM
    look.widths(sheet, [('B', 46)] + [(look.letter(3 + i), 18) for i in range(len(columns))])
    look.title(sheet, f'CURRENT vs INCOMING PROPOSALS · {ctx["client"]}')
    note = 'The CURRENT column is linked to the In-Force Snapshot — do not type over it. Compare laser liability and '
    note += 'MAXIMUM ANNUAL LIABILITY, never premium alone. ' + look.ROUNDTRIP_NOTE
    look.put(sheet, 2, 2, note, look.WRAP)
    census = rows['CENSUS']
    look.put(sheet, census, 2, 'Census used for all columns', look.BOLD)
    look.link(sheet, census, 3, f'={look.ref("C" + str(snap["HC"]))}', ctx['lives'] or 0)
    look.put(sheet, census, 4, 'employees')
    look.link(sheet, census, 5, f'={look.ref("C" + str(snap["MO"]))}', ctx['months'])
    look.put(sheet, census, 6, 'months')
    if not columns:
        look.put(sheet, rows['HEAD'], 2, 'No stop-loss plans on this deal yet.')
        return
    look.put(sheet, rows['HEAD'], 2, 'Variable', look.BOLD)
    for i, (heading, plan) in enumerate(columns):
        col = 3 + i
        cell = look.text(sheet, rows['HEAD'], col, heading)
        cell.style = {**cell.style, 'bold': True, 'pattern': 1, 'bg_color': look.LIGHT}
        linked = current is not None and i == 0
        _inputs(sheet, rows, snap, col, plan, linked, ctx['shared_rows'])
        _formulas(sheet, rows, col, plan)
        if current is not None:
            _deltas(sheet, rows, col, plan, linked)
    span = 1 + len(columns)
    for row, words in (
        ('BAND_PREM', PREMIUM_BAND),
        ('BAND_AGG', 'AGGREGATE ATTACHMENT'),
        ('BAND_ADMIN', 'ADMIN'),
        ('BAND_LASER', LASER_BAND),
        ('BAND_COST', 'ANNUAL COST COMPARISON'),
    ):
        look.section(sheet, rows[row], words, span=span)
    look.put(sheet, rows['LASER_NOTE'], 2, 'Lasers by position only — no claimant ids, no PHI. Carriers laser '
             'different people at different amounts; enter each option’s own figure on the shared rows.')  # fmt: skip
    for row, words in LABELS:
        look.put(sheet, rows[row], 2, words)
    look.put(sheet, rows['MAL'], 2, 'MAXIMUM ANNUAL LIABILITY (SL + admin + attachment + lasers)', look.NAVY_BOLD)
    look.put(sheet, rows['HEAD_LASER'], 2, 'Laser', look.BOLD)
    for n in range(1, ctx['shared_rows'] + 1):
        look.text(sheet, rows['LASER_FIRST'] + n - 1, 2, look.laser_label(n))
    look.put(
        sheet,
        rows['NOTE'],
        2,
        'Negative numbers mean the proposal is lower than the current contract. A column '
        'with no specific rate stays blank all the way through — it cannot report a saving it never quoted.',
    )
    look.put(sheet, rows['PREFERRED'], 2, 'Preferred option', look.BOLD)
    look.put(sheet, rows['WHY'], 2, 'Why (rate vs laser vs run-in vs TPA)', look.BOLD)
    sheet.freeze = (7, 3)
