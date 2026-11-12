"""The client spreadsheet's formula templates, ported verbatim from old Vantage (891f1b3: `presentation_workbook` and
`presentation_bank`; plan.md §9.4, J147, J148). Each returns one cell's formula text; `grammar.check` holds them to
the closed list IF, OR, AND, SUM, ROUND, INDEX, MATCH, IFERROR, MIN, MAX and HYPERLINK. Each has its figure in quotes'
math, which the tab writers store as the cell's result and the tests (and the Recalc lane) hold the formula to.

Every cell a client can type into reads as quotes' math reads its input. A value with no number in it (empty, or
text such as "TBD", "N/A" or "-") is missing, never a #VALUE!: `no_number` is the test for a rate, a stated premium,
a monthly or annual figure and a credit; a count is read through SUM, which skips text, so a count with no number
counts 0. An enrolled tier is a count that is not zero. There is no SUMPRODUCT: an unrated enrolled tier falls back
to the stated premium or blank (J.5 B33).
"""

from .grammar import sheet_ref


def no_number(*refs):
    """The terms, for one OR(...), that are TRUE when any of these cells holds no number: it is empty, holds text,
    or holds a formula's own "". Text is greater than "" and a number is not."""
    return ','.join(f'{ref}="",{ref}>""' for ref in refs)


def count(n, row):
    """A tier count as a number: SUM of the one cell skips text, so a count typed as "-" counts 0."""
    return f'SUM(${n}${row})'


# --- A rates tab (two columns a plan: its counts `n`, its rates `v`) -------------------------------------------------
def total(n, v, tiers, stated_row=None):
    """A plan's monthly total. Blank when nobody is enrolled. With an enrolled tier unrated, the carrier-stated premium
    rounded half up when there is a stated row, else blank. Otherwise the counts times the rates, rounded."""
    guards = ','.join(f'AND({count(n, row)}<>0,OR({no_number(v + str(row))}))' for row in tiers)
    products = '+'.join(f'IF({count(n, row)}=0,0,{count(n, row)}*{v}{row})' for row in tiers)
    stated = f'{v}{stated_row}'
    fallback = f'IF(OR({no_number(stated)}),"",ROUND({stated},0))' if stated_row else '""'
    return f'=IF(SUM(${n}${tiers[0]}:${n}${tiers[-1]})=0,"",IF(OR({guards}),{fallback},ROUND({products},0)))'


def annual(v, monthly_row):
    """Twelve times the monthly total, blank when it holds no number."""
    monthly = f'{v}{monthly_row}'
    return f'=IF(OR({no_number(monthly)}),"",{monthly}*12)'


def delta(v, row, cv, base_row):
    """A figure against the current plan's, blank if either holds no number."""
    value, base = f'{v}{row}', f'${cv}${base_row}'
    return f'=IF(OR({no_number(value, base)}),"",{value}-{base})'


def pct(v, row, cv, base_row):
    """The same change as a fraction, to three places (the one-decimal percentage quotes' math gives). Blank when
    either holds no number, or for a zero base."""
    value, base = f'{v}{row}', f'${cv}${base_row}'
    return f'=IF(OR({no_number(value, base)},{base}=0),"",ROUND(({value}-{base})/{base},3))'


def net(v, annual_row, credit_row):
    """A package's annual less its first-year credit: blank when the year holds no number, the year itself when the
    credit holds none, blank when the credit is larger than the year."""
    year, credit = f'{v}{annual_row}', f'{v}{credit_row}'
    return f'=IF(OR({no_number(year)}),"",IF(OR({no_number(credit)}),{year},IF({credit}>{year},"",{year}-{credit})))'


# --- The Compare, Composite Rates and All Plans tabs (references may name another tab) -------------------------------
def total_over(counts, rates, stated=None):
    """A plan's monthly total over four count cells and four rate cells (`total`'s rule)."""
    guards = ','.join(f'AND(SUM({c})<>0,OR({no_number(v)}))' for c, v in zip(counts, rates, strict=True))
    products = '+'.join(f'IF(SUM({c})=0,0,SUM({c})*{v})' for c, v in zip(counts, rates, strict=True))
    fallback = f'IF(OR({no_number(stated)}),"",ROUND({stated},0))' if stated else '""'
    return f'=IF(SUM({",".join(counts)})=0,"",IF(OR({guards}),{fallback},ROUND({products},0)))'


def lookup(bank, column, first, last, key):
    """INDEX of one All Plans column at the row whose label is the value in `key` (an exact MATCH, case ignored)."""
    prefix = sheet_ref(bank)
    return f'INDEX({prefix}${column}${first}:${column}${last},MATCH({key},{prefix}$A${first}:$A${last},0))'


def looked_up(found):
    """A looked-up cell: blank when nothing is picked, the pick is not on the list, or its cell is empty."""
    return f'=IFERROR(IF({found}="","",{found}),"")'


def base_pct(slot, base, value, base_value):
    """A column's change against the plan a base picker names: blank when the column is the base, when the value holds
    no number, and (through IFERROR) when the base is not picked, has no figure or has a zero one."""
    return f'=IFERROR(IF(OR({slot}={base},{no_number(value)}),"",ROUND(({value}-{base_value})/{base_value},3)),"")'


def _no_dollars(amounts):
    """TRUE when no tier's dollar input holds a number: the percents apply only then."""
    return ','.join(f'OR({no_number(ref)})' for ref in amounts)


def employees(counts, ee, share, amounts):
    """The employer's cost toward the employee rate under the percent; blank once a tier holds dollars."""
    n = f'SUM({",".join(counts)})'
    return (
        f'=IF(AND({_no_dollars(amounts)}),IF({n}=0,"",IF(OR({no_number(ee)}),"",'
        f'IF(OR({no_number(share)}),"",ROUND({n}*{ee}*{share},0)))),"")'
    )


def dependents(counts, rates, share, amounts):
    """The employer's cost toward the dependent part of each tier under the percent; blank once a tier holds dollars.
    `counts` and `rates` are in tier order, so the first rate is the employee rate every gap is measured from."""
    n = f'SUM({",".join(counts)})'
    ee = rates[0]
    missing = ','.join(f'AND(SUM({c})<>0,OR({no_number(r, ee)}))' for c, r in zip(counts[1:], rates[1:], strict=True))
    gaps = '+'.join(f'IF(SUM({c})=0,0,SUM({c})*MAX(0,{r}-{ee}))' for c, r in zip(counts[1:], rates[1:], strict=True))
    return (
        f'=IF(AND({_no_dollars(amounts)}),IF(OR({n}=0,{no_number(share)}),"",'
        f'IF(OR({missing}),"",ROUND(({gaps})*{share},0))),"")'
    )


def tier_pay(tier_count, rate, amount, amounts):
    """One tier's cost under the dollars the employer pays it: blank until a tier holds dollars, with nobody in the
    tier or no rate; 0 for a tier left blank; never more than the rate."""
    return (
        f'=IF(AND({_no_dollars(amounts)}),"",IF(SUM({tier_count})=0,"",'
        f'IF(OR({no_number(rate)}),"",IF(OR({no_number(amount)}),0,'
        f'ROUND(SUM({tier_count})*MAX(0,MIN({amount},{rate})),0)))))'
    )


def linked(ref):
    """Another cell's value, blank when it is blank. A bare `=ref` to an empty cell is 0 in Excel, which a guard reads
    as a number (a Composite Rates card would then read every blank dollar input as $0 and switch to dollars)."""
    return f'=IF({ref}="","",{ref})'


def employer_total(*parts):
    """The sum of the parts that hold a number."""
    blank = ','.join(f'OR({no_number(part)})' for part in parts)
    return f'=IF(AND({blank}),"",SUM({",".join(parts)}))'


def employee_total(monthly, employer):
    return f'=IF(OR({no_number(monthly, employer)}),"",MAX(0,{monthly}-{employer}))'
