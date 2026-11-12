"""`GET deals/{id}/proposal/pages/?line=&preset=`: "What the client will see" (plan.md §7.12; F37–F39, F45, F46,
J5–J13; slice 14).

One line's proposal page by page as the PowerPoint prints it (`pages.sequence`, the one splitter): each page with its
plans as columns, the columns' facts and words (`page_columns`), the preset's rows as formatted text (`page_cells`),
the plans off the proposal (`others`) for the plan picker, and where "＋ Add a plan" would land. The plans and their
order are quotes' (`presented()`, `order.layout`); a line the coverage intent keeps off presents nothing (J2). Reads
only, in a fixed number of queries at any plan count (Q.3 #2, #4).

{line, label, preset, per_page, cap, room, nothing_starred, several, off, quotes, currents: [{id, number, words,
 monthly}], presented_ids, pages: [{n, part, label, caption, carrier, continued, current_id, full, plan_ids,
 repeat_ids}], plans: [column facts, in the line's order], rows: [{key, label, section, cells}], others: [picker row],
 landing: {'': note, '<current id>': note}, full_words}
"""

from deals import lines
from intake import coverage as intent
from intake.selectors import line_facts
from quotes import presented
from quotes import selectors as quotes

from . import line_layout, page_cells
from . import page_columns as cols
from . import pages as splitter

LIGHT = ('plan_id', 'kind', 'carrier', 'name', 'words', 'chips', 'links', 'group', 'stays_with', 'stays_words')
LIGHT += ('why_not', 'on', 'starred', 'recommended', 'monthly', 'change', 'page')


def page_label(page, label):
    more = ' (continued)' if page['continued'] else ''
    if page['part'] == 'renewal':
        return f'{label} renewal{more}'
    if page['caption']:
        return f'{page["caption"]}{more}'
    if page['carrier']:
        return f'{page["carrier"]}{more}'
    return f'{label} comparison'


def landing(pages, current=None, per_page=splitter.PER_PAGE):
    """Where one more plan would land, in the old screen's words ("Page 1 is full. One more plan starts page 2."):
    on the line's options pages, or (`current`) on the pages of that current plan's options."""
    if not pages:
        return ''
    options = [
        (number, page)
        for number, page in enumerate(pages, start=1)
        if page['part'] == 'options' and (current is None or page['current_id'] == current)
    ]
    if not options:
        count = len(pages)
        if len(pages[-1]['plan_ids']) >= per_page:
            return f'Page {count} is full. One more plan starts page {count + 1}.'
        return f'One more plan starts a page of its own after page {count}.'
    number, page = options[-1]
    held = len(page['plan_ids'])
    if held >= per_page:
        return f'Page {number} is full. One more plan starts page {number + 1}.'
    room = per_page - held
    return f'Page {number} has room for {room} more plan{"" if room == 1 else "s"}.'


def _off(deal, line, state):
    """The intent's reason for keeping the line off the client's documents, or None."""
    _states, off = line_facts(deal, {line: {'sold': any(plan.sold for plan in state.plans)}})
    return off.get(line)


def payload(deal, line, preset):
    state = quotes.line_state(deal, line)
    data, results = state.data, state.results
    label = lines.label(line)
    off = _off(deal, line, state) if state.plans else None
    layout = line_layout.layout_of(line_layout.stored_config(deal))
    laid = line_layout.lay_out(state, off, layout, line_layout.tops(deal, [line]).get(line, 0))
    rows, shown, numbers, pages = laid.rows, laid.shown, laid.numbers, laid.pages
    on = {plan.id for plan in shown}
    ctx = {
        'numbers': numbers,
        'options': laid.options,
        'first_page': splitter.first_pages(pages),
        'arrows': cols.arrows(shown, data),
        'label': label,
        'on': on,
    }
    others = [cols.facts(plan, data, results, rows, ctx) for plan in data.plans if plan.id not in on]
    starred = presented.has_stars(data)
    return {
        'line': line,
        'label': label,
        'preset': preset,
        'per_page': splitter.PER_PAGE,
        'cap': presented.MAX_COLUMNS,
        'room': presented.room(data),
        'nothing_starred': not starred,
        'several': len(data.current) >= 2,
        'off': intent.OFF_LABELS.get(off) if off else None,
        'quotes': sum(1 for plan in data.plans if plan.role != 'current'),
        'currents': [
            {'id': plan.id, 'number': n, 'words': cols.words(rows[plan.id]), 'monthly': cols.premium(plan, results)[0]}
            for n, plan in enumerate(data.current, start=1)
        ],
        'presented_ids': [plan.id for plan in shown],
        'pages': [
            {
                'n': n,
                **page,
                'label': page_label(page, label),
                'full': len(page['plan_ids']) >= splitter.PER_PAGE,
            }
            for n, page in enumerate(pages, start=1)
        ],
        'plans': [cols.facts(plan, data, results, rows, ctx) for plan in shown],
        'rows': page_cells.rows(line, preset, [rows[plan.id] for plan in shown]),
        'others': [{key: entry[key] for key in LIGHT} for entry in others],
        'landing': {'': landing(pages), **{str(pid): landing(pages, pid) for pid in numbers}},
        'full_words': presented.refusal(data, label, 1, 'take one off first') if starred else None,
    }
