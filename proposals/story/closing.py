"""What happens next, the thank-you page and the appendix's important information (plan.md §9.5; J138; old Vantage
891f1b3 `proposal_presentation._next_steps_page`, `_calendar_page`, `_closing`, `_disclaimers_page`). Pure.

Next steps are the producer's dates and words. The meeting calendar is the firm's (Django admin until slice 34) and
prints nothing until written (OQ41). The thank-you page is never hidden: it says the disclaimer's line. Important
information carries the standing paragraphs every client file carries (old `disclaimers.DOCUMENT`).
"""

from ..layout import flowables, furniture, tokens
from ..layout import table as tb
from . import look


def next_steps(facts):
    steps = facts['next_steps']
    if not steps:
        return []
    colours = look.colours_of(facts)
    size = 14
    rows = [look.heads(['When', 'What happens'], colours, size, center_from=9)]
    for step in steps:
        when = look.long_date(look.iso_date(step.get('date') or '')) if step.get('date') else ''
        rows.append(
            {
                'kind': 'plain',
                'cells': [
                    tb.cell(when, size, colours['ink'], True, leading=size + 4),
                    tb.cell(step.get('text') or '', size, colours['ink'], leading=size + 4),
                ],
            }
        )
    return [[look.title('Next steps'), look.grid(rows, look.shares([0.26, 0.74]), colours, pad=11)]]


def calendar(facts):
    meetings = facts['firm']['calendar']
    if not meetings:
        return []
    colours = look.colours_of(facts)
    size, ink = 12, colours['ink']
    rows = [look.heads(['Meeting', 'What we cover', 'When'], colours, size, center_from=9)]
    for meeting in meetings:
        topics = [str(topic) for topic in meeting.get('topics') or [] if str(topic).strip()]
        # Each topic a line at the cell's leading, as the old cell held a paragraph a topic.
        lead = size + 4
        cells = [
            tb.cell(str(meeting.get('meeting') or ''), size, ink, True, leading=lead),
            tb.cell('\n'.join(topics), size, ink, leading=lead),
            tb.cell(str(meeting.get('when') or ''), size, ink, leading=lead),
        ]
        rows.append({'kind': 'plain', 'cells': cells})
    table = look.grid(rows, look.shares([0.26, 0.5, 0.24]), colours, pad=6)
    return [[look.title('How we work together through the year'), table]]


def thank_you(facts):
    """The closing page: who to call, the disclaimer's line and the firm's copyright."""
    agency = facts['agency']
    colours = look.colours_of(facts)
    lines = []
    if facts['prepared_by']:
        lines.append(facts['prepared_by'])
    contact = ' · '.join(bit for bit in (agency['phone'], agency['email']) if bit)
    if contact:
        lines.append(contact)
    small = [f'{tokens.DISCLAIMER} Important information follows.']
    if agency['name']:
        year = facts['prepared_on'].year if facts['prepared_on'] else ''
        small.append(f'© {year} {agency["name"]}'.replace('©  ', '© '))
    picture = facts['pictures'].get('closing')
    placed = furniture.closing_items(
        {'heading': 'Thank you', 'lines': lines, 'small': small},
        colours,
        logo_src=agency['logo'],
        draft=facts['draft'],
        picture=picture,
    )
    return [[flowables.FullPage(placed, ground=furniture.dark_ground(colours, mark=not picture), title='Thank you')]]


def important(facts):
    colours = look.colours_of(facts)
    paragraphs = [look.para(text, 'rationale', colours) for text in tokens.DOCUMENT_DISCLAIMERS]
    return [[look.title('Important information'), *paragraphs]]
