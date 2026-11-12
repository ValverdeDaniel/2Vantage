"""The request in words (plan.md §9.9–§9.11; K99, K103, K104). Pure over one request (`context.Request`).

- `request_summary(ctx, on_form=False)`: in full — the carriers asked and the lines each can quote, "Also please
  quote", the carriers the form does not print, the lines, the funding, the commission by line and the notes — it is
  the Warner draft's extra text and the packet's `Quote request summary.txt`; `on_form=True` is what Warner's own Notes
  cell carries on the 2–50 and 51+ forms, where the matrix and the boxes say the rest: only the commission by line,
  and the notes (old `market/rfp.request_summary`, 891f1b3).
- `summary_file(ctx)`: the packet's summary file: the group, the dates, then the summary (Warner route only, K103).
- `readme(ctx, members, today)`: the packet's README: the group, the date, the files, the lines and funding asked and
  the notes, signed with the agency's name. It names no carrier and carries no warnings (D-143; K103, bugs 21, 23).
- Dates: `long_date` "April 1, 2027", `short_date` "04/01/2027"; short lines from §4.1 "Short".
"""

from datetime import date

from deals import carriers as identities
from deals import lines

from . import carriers, request


def long_date(value):
    value = as_date(value)
    return f'{value:%B} {value.day}, {value.year}' if value else ''


def short_date(value):
    value = as_date(value)
    return value.strftime('%m/%d/%Y') if value else ''


def as_date(value):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def short_lines(keys):
    return [lines.BY_KEY[key]['short'] if key in lines.BY_KEY else key for key in keys]


def line_labels(keys):
    return [lines.label(key) for key in keys]


def funding_labels(keys):
    return [request.FUNDING_LABELS[key] for key in keys if key in request.FUNDING_LABELS]


def off_form(ctx):
    """The picked carriers Warner's form does not print (they ride its "Additional carriers" line)."""
    return [ctx.chip[key]['name'] for key in ctx.picked if not carriers.ATTRIBUTES[key]['on_form']]


def request_summary(ctx, on_form=False):
    out = []
    if not on_form:
        picked = [ctx.chip[key] for key in ctx.picked]
        if picked:
            named = [row['name'] + (f' ({", ".join(row["line_labels"])})' if row['line_labels'] else '')
                     for row in picked]  # fmt: skip
            out.append('Carriers requested: ' + ' · '.join(named))
        if ctx.other_text():
            out.append(f'Also please quote: {ctx.other_text()}')
        if off_form(ctx):
            out.append(f'Not printed on this form: {", ".join(off_form(ctx))}')
        if ctx.lines:
            out.append('Lines: ' + ', '.join(line_labels(ctx.lines)))
        if ctx.funding:
            out.append('Funding: ' + ', '.join(funding_labels(ctx.funding)))
    breakdown = ctx.commission[1]
    if len(breakdown) > 1:
        out.append('Commission requested — ' + ' · '.join(breakdown))
    notes = ctx.stored['notes']
    if notes:
        out += ([''] if out else []) + [notes]
    return '\n'.join(out)


def summary_file(ctx):
    """`Quote request summary.txt` (Warner route only), or '' when there is nothing to say."""
    body = request_summary(ctx)
    if not body:
        return ''
    head = [f'Quote request — {ctx.group_name}']
    if ctx.deal.effective_date:
        head.append(f'Requested effective date: {short_date(ctx.deal.effective_date)}')
    if ctx.stored['due_date']:
        head.append(f'Quotes due: {short_date(ctx.stored["due_date"])}')
    return '\n'.join([*head, '', body]) + '\n'


def readme(ctx, names, today):
    """`README.txt`: `names` is [(file name in the zip, label)]."""
    count = len(names)
    out = [
        f'RFP packet — {ctx.group_name}',
        f'Prepared {long_date(today)}',
        '',
        f'{count} file{"" if count == 1 else "s"} in this packet:',
        *[f'  - {name} — {label}' for name, label in names],
        '',
    ]
    if ctx.lines:
        out.append(f'Lines requested: {", ".join(line_labels(ctx.lines))}')
    if ctx.funding:
        out.append(f'Funding: {", ".join(funding_labels(ctx.funding))}')
    if ctx.stored['notes']:
        out += ['', 'Notes:', ctx.stored['notes']]
    out += ['', f'Prepared by {ctx.agency.name or "the agency"}.']
    return '\n'.join(out) + '\n'


def carrier_name(key):
    found = identities.BY_KEY.get(key)
    return found['name'] if found else key
