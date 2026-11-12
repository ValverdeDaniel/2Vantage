"""The cost rows of a Compare tab and of each Composite Rates card (plan.md §9.4; J148; old `presentation_bank`
`_CompareSheet._premium` … `_notes` at 891f1b3): the shared counts in B, each slot's looked-up rates, the two totals,
the % rows against the base plans, Bryke's employer contribution (two percents, or the dollars a month for each tier;
the dollars win once any is filled), and the notes.

Each formula's stored result is quotes' figure for the slot's pick: the monthly premium at the shared counts
(`all_plans.listed`), `m.change` / `m.tier_rate_change` for the % rows, and `quotes.math.contribution` for the
employer's share, so the file's results are the app's figures (rule 5) and LibreOffice recalculates to them.
"""

from quotes import math as m
from quotes.math import TIERS, contribution

from .. import cells, formulas
from .. import styles as s
from ..grammar import sheet_ref
from ..model import column_letter
from .all_plans import fraction
from .common import DISCLAIMER, ENROLL_NOTE, TIER_LABEL, table_note_rows

C = s.COMPACT
COMPARE_NOTE = (
    "Pick any quoted plan in the Plan Name row (▾) of each column; the list is the '{tab}' tab. Counts and the "
    'employer contribution in blue can be changed, and every figure recalculates.'
)
CONTRIB_NOTE = (
    "Employer contribution: a percent of the employee rate and of the dependent cost (each tier's rate less the "
    'employee rate), or the dollars a month the employer pays for each tier. The dollars are used when any is filled, '
    "never more than a plan's rate."
)
LINKED_NOTE = "The counts follow the current plan's counts on the '{tab}' tab; type over them to try other numbers."
SEVERAL_NOTE = "Enrolled counts: every current plan's people together."
NOTE_COLUMNS = 12  # a note spans A:B and the first five slots, one printed page


def enroll_note(line, linked_title):
    if linked_title:
        return LINKED_NOTE.format(tab=linked_title)
    if not line.people:
        return ENROLL_NOTE['none']
    if len([plan for plan in line.plans if plan.role == 'current']) > 1:
        return SEVERAL_NOTE
    return ENROLL_NOTE.get(line.people_source) or ENROLL_NOTE['none']


class CostRows:
    """Mixed into the Compare and Composite Rates sheets, which supply `sheet`, `rows`, `m` (the page's map), `amap`,
    `bank`, `line`, `ctx`, `shared`, `listed`, `pid`, `found_value`, `_found`, `_pick`, `_base`, `_label`,
    `_navy_label`, `_slot`, `_height`, `base_values`, `titles` and `LABEL_CHARS`."""

    # -- what a slot's cells hold ------------------------------------------------------------------------------------
    def slot_rates(self, slot):
        row = self.listed.get(self.pid(slot))
        return dict(row['rates']) if row else dict.fromkeys(TIERS)

    def slot_monthly(self, slot):
        row = self.listed.get(self.pid(slot))
        return row['monthly'] if row else None

    def base_pid(self, which):
        return self.pid_of.get(str(self.base_values[which]).lower())

    def contrib(self):
        found = self.bank['contrib'] or {}
        return found.get('ee_pct'), found.get('dep_pct'), found.get('tier')

    # -- the rates block ---------------------------------------------------------------------------------------------
    def _count_refs(self):
        return [f'$B${row}' for row in self.rows['tiers']]

    def _premium(self):
        sheet, rows, bcols = self.sheet, self.rows, self.amap['cols']
        head = rows['band']
        for col, word in ((1, 'Monthly Rates'), (2, 'Enrollment')):
            cells.text(
                sheet,
                head,
                col,
                word,
                font=C['white'],
                fill=s.FILL_NAVY,
                border=s.THIN,
                align=s.label_align() if col == 1 else s.CENTER,
            )
        for slot in self.m['slots']:
            cells.text(
                sheet, head, slot['col'], 'Rates', font=C['white'], fill=s.FILL_NAVY, border=s.THIN, align=s.CENTER
            )
            cells.blank(sheet, head, slot['right'], fill=s.FILL_NAVY, border=s.THIN)
            cells.merge_pair(sheet, head, slot['col'], slot['right'])
        sheet.heights[head] = s.COMPACT_ROW_H
        for tier, row in zip(TIERS, rows['tiers'], strict=True):
            self._label(row, TIER_LABEL[tier], fill=s.FILL_WHITE)
            self._count(row, tier)
            for slot in self.m['slots']:
                template = formulas.looked_up(self._found(bcols['rates'][tier], self._pick(slot)))
                self._slot(row, slot, template, self.found_value(slot, 'rates', tier), s.RATE_FLEX, fill=s.FILL_GREEN)
            sheet.heights[row] = s.COMPACT_ROW_H
        if rows['g']:
            self._label(rows['g'], 'Carrier-stated monthly premium', fill=s.FILL_WHITE)
            for slot in self.m['slots']:
                template = formulas.looked_up(self._found(bcols['stated'], self._pick(slot)))
                self._slot(
                    rows['g'], slot, template, self.found_value(slot, 'stated'), s.MONEY_WHOLE, fill=s.FILL_GREEN
                )
            sheet.heights[rows['g']] = self._height([('Carrier-stated monthly premium', self.LABEL_CHARS)])
        counts = self._count_refs()
        stated = rows['g']
        for slot in self.m['slots']:
            v = column_letter(slot['col'])
            monthly = self.slot_monthly(slot)
            total = formulas.total_over(counts, [f'{v}{r}' for r in rows['tiers']], f'{v}{stated}' if stated else None)
            slot['_tm'] = (total, monthly)
            slot['_ta'] = (formulas.annual(v, rows['tm']), m.annual(monthly))
        self._calc_row(rows['tm'], 'Total Monthly Premium', s.MONEY_WHOLE, '_tm', bold=True)
        self._calc_row(rows['ta'], 'Total Annual Premium', s.MONEY_WHOLE, '_ta', bold=True)

    def _count(self, row, tier):
        """A shared tier count, blue on light blue: a link to the current plan's count on the rates tab when the line
        shows one there (one edit flows through, and the cell can still be typed over); otherwise an input."""
        value = self.shared['counts'].get(tier)
        link = self.shared['link']
        if link:
            title, letter, tiers = link
            source = tiers[TIERS.index(tier)]
            cells.formula(
                self.sheet,
                row,
                2,
                f'={sheet_ref(title)}${letter}${source}',
                value or 0,
                s.COUNT,
                sheets=self.ctx.sheets,
                font=C['input'],
                fill=s.FILL_LABEL,
                border=s.THIN,
                align=s.CENTER,
            )
        else:
            cells.number(
                self.sheet, row, 2, value, s.COUNT, font=C['input'], fill=s.FILL_LABEL, border=s.THIN, align=s.CENTER
            )
        cells.unlock(self.sheet, row, 2)

    def _input(self, row, name, value, num):
        """One contribution input in B: a blue number the client types over."""
        cells.number(self.sheet, row, 2, value, num, font=C['input'], fill=s.FILL_LABEL, border=s.THIN, align=s.CENTER)
        cells.unlock(self.sheet, row, 2)

    def _calc_row(self, row, label, num, key, *, bold=False):
        """A computed row: a navy label, each slot's (template, result) under `key` on green."""
        self._navy_label(row, label)
        look = C['bold'] if bold else C['body']
        for slot in self.m['slots']:
            template, value = slot[key]
            self._slot(row, slot, template, value, num, fill=s.FILL_GREEN, font=look)
        self.sheet.heights[row] = s.COMPACT_ROW_H

    # -- the two % rows ----------------------------------------------------------------------------------------------
    def _change(self, slot, which, half):
        """A % half's stored result: '' for the base itself, a missing value or base, else quotes' change."""
        pid, base = self.pid(slot), self.base_pid(which)
        if pid is None or base is None or pid == base:
            return None
        if half == 'ee':
            found = m.tier_rate_change(self.line.data.by_id[pid], self.line.data.by_id[base])['EE']
            return fraction(found)
        base_monthly = self.listed[base]['monthly'] if base in self.listed else None
        return fraction(m.change(self.slot_monthly(slot), base_monthly))

    def _changes(self):
        sheet, rows, bcols = self.sheet, self.rows, self.amap['cols']
        ee_row, plan_row = rows['tiers'][0], rows['plan']
        for row, label, base_row, which in (
            (rows['ce'], '% Difference from Current', rows['base_current'], 'current'),
            (rows['re'], '% Difference from Renewal', rows['base_renewal'], 'renewal'),
        ):
            self._navy_label(row, label)
            base = self._base(base_row)
            for slot in self.m['slots']:
                left = column_letter(slot['col'])
                pick = f'{left}${plan_row}'
                for col, value, bank_col, num, half in (
                    (slot['col'], f'{left}{ee_row}', bcols['rates']['EE'], s.CHANGE_EE_ONLY, 'ee'),
                    (slot['right'], f'{left}{rows["tm"]}', bcols['monthly'], s.CHANGE_TOTAL, 'total'),
                ):
                    template = formulas.base_pct(pick, base, value, self._found(bank_col, base))
                    cells.formula(
                        sheet,
                        row,
                        col,
                        template,
                        self._change(slot, which, half),
                        num,
                        sheets=self.ctx.sheets,
                        font=C['bold'],
                        fill=s.FILL_GREEN,
                        border=s.THIN,
                        align=s.CENTER,
                    )
            sheet.heights[row] = s.COMPACT_ROW_H

    # -- the employer contribution -----------------------------------------------------------------------------------
    def _contribution(self):
        sheet, rows = self.sheet, self.rows
        cells.text(sheet, rows['cband'], 1, 'Employer Contribution', font=C['bold'], align=s.label_align(0))
        sheet.heights[rows['cband']] = s.COMPACT_ROW_H
        ee_pct, dep_pct, dollars = self.contrib()
        amounts = dict(dollars) if dollars else dict.fromkeys(TIERS)
        inputs = [
            (rows['ee_pct'], 'ee_pct', 'Employees', ee_pct, s.PCT_1DP),
            (rows['dep_pct'], 'dep_pct', 'Dependents', dep_pct, s.PCT_1DP),
        ]
        inputs += [
            (row, ('tier_pay', index), f'Or $ a month — {TIER_LABEL[tier]}', amounts.get(tier), s.MONEY_CENTS)
            for index, (tier, row) in enumerate(zip(TIERS, rows['tier_pay'], strict=True))
        ]
        for row, name, label, value, num in inputs:
            self._navy_label(row, label)
            self._input(row, name, value, num)
            sheet.heights[row] = self._height([(label, self.LABEL_CHARS - 4)])
        counts, tiers = self._count_refs(), rows['tiers']
        pct = {name: f'$B${rows[name]}' for name in ('ee_pct', 'dep_pct')}
        cells_amounts = [f'$B${row}' for row in rows['tier_pay']]
        shared = self.shared['counts']
        for slot in self.m['slots']:
            v = column_letter(slot['col'])
            rates = self.slot_rates(slot)
            employees = contribution.for_employees(shared, rates, ee_pct, amounts)
            dependents = contribution.for_dependents(shared, rates, dep_pct, amounts)
            slot['_er_ee'] = (formulas.employees(counts, f'{v}{tiers[0]}', pct['ee_pct'], cells_amounts), employees)
            slot['_er_dep'] = (
                formulas.dependents(counts, [f'{v}{r}' for r in tiers], pct['dep_pct'], cells_amounts),
                dependents,
            )
            parts = [employees, dependents]
            for index, (count, tier_row, tier) in enumerate(zip(counts, tiers, TIERS, strict=True)):
                paid = contribution.for_tier(shared.get(tier), rates[tier], amounts.get(tier), amounts)
                parts.append(paid)
                slot[f'_tier{index}'] = (
                    formulas.tier_pay(count, f'{v}{tier_row}', cells_amounts[index], cells_amounts),
                    paid,
                )
            employer = contribution.employer_total(*parts)
            part_refs = [f'{v}{row}' for row in (rows['er_ee'], rows['er_dep'], *rows['tier_pay'])]
            slot['_er_total'] = (formulas.employer_total(*part_refs), employer)
            slot['_ee_total'] = (
                formulas.employee_total(f'{v}{rows["tm"]}', f'{v}{rows["er_total"]}'),
                contribution.employee_total(self.slot_monthly(slot), employer),
            )
            slot['_er_annual'] = (formulas.annual(v, rows['er_total']), m.annual(employer))
        for row, key in ((rows['er_ee'], '_er_ee'), (rows['er_dep'], '_er_dep')):
            self._results_row(row, key)
        for index, row in enumerate(rows['tier_pay']):
            self._results_row(row, f'_tier{index}')
        self._calc_row(rows['er_total'], 'Employer Total (monthly)', s.MONEY_WHOLE, '_er_total', bold=True)
        self._calc_row(rows['ee_total'], 'Employee Total (monthly)', s.MONEY_WHOLE, '_ee_total')
        self._calc_row(rows['er_annual'], 'Employer Total (annual)', s.MONEY_WHOLE, '_er_annual')

    def _results_row(self, row, key):
        """The employer's cost on an input's own row, each slot's formula on green."""
        for slot in self.m['slots']:
            template, value = slot[key]
            self._slot(row, slot, template, value, s.MONEY_WHOLE, fill=s.FILL_GREEN)

    # -- the notes ---------------------------------------------------------------------------------------------------
    def _notes(self):
        first, last = self.rows['notes']
        found = [(text, C['body']) for text in table_note_rows(self.line)]
        found += [(COMPARE_NOTE.format(tab=self.titles['bank']), C['italic']), (DISCLAIMER, C['bold_italic'])]
        if self.rows['tiers']:
            found.append((CONTRIB_NOTE, C['body']))
            link = self.shared['link']
            found.append((enroll_note(self.line, link[0] if link else None), C['body']))
        cells.spacer(self.sheet, first - 1)
        for row, (text, look) in zip(range(first, last + 1), found, strict=False):
            cells.text(self.sheet, row, 1, text, font=look, align=s.LEFT)
            cells.merge_pair(self.sheet, row, 1, NOTE_COLUMNS)
            self.sheet.heights[row] = cells.row_height(
                [(text, 200)], minimum=s.COMPACT_ROW_H, line_pt=s.COMPACT_LINE_PT
            )
