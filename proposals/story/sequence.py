"""The client deck's story, page by page (plan.md §9.5; J123–J138, J165; old Vantage 891f1b3
`proposal_presentation.presentation_story`). Pure: Facts in, pages of flowables out.

The order answers a decision-maker's questions first, then shows the work:

    cover · agenda
    who we are          About the firm, Your team
    the answer          the overview, what we negotiated, the premiums charted, the executive summary
    how we got here     plan experience, the markets we asked
    your coverage       line by line: the renewal set, the options, one table per plan set, the recommendation
    what happens next   next steps, the meeting calendar
    thank you
    appendix            bios, important information

Each section is its pages; a section with none is not named, so the agenda only promises what follows. The agenda and
the section dividers print together, only when switched on and with three or more sections (J124). A page the
producer switched off (`output.pages`) does not print; a page with no facts does not print either, and its section
goes with it. The renewal history page waits with past plan years (J129). The thank-you page is never hidden.
"""

from ..layout import flowables, furniture
from . import answer, closing, coverage, firm, glance, line_pages, look, opening


def _sections(facts, colours):
    switched = facts['pages']

    def on(name):
        return switched.get(name, True) is not False

    plans = {pid: plan for line in facts['lines'] for pid, plan in line['plans'].items()}
    sections = []

    def add(key, title, sub, pages):
        pages = [page for page in pages if page]
        if pages:
            sections.append({'key': key, 'title': title, 'sub': sub, 'pages': pages})

    who = (firm.about(facts) if on('about') else []) + (firm.team(facts) if on('team') else [])
    add('about', f'About {facts["agency"]["name"] or "us"}', 'Who we are and who will look after you', who)
    rows = glance.rows(facts['glance_facts'])
    overview = coverage.overview(facts, plans)
    found = overview + answer.negotiation(facts, rows, plans) + answer.chart(facts, rows)
    found += answer.summary(facts, bool(overview))
    picked = bool(rows)
    if facts['renewal'] and facts['year']:
        heading = f'Your {facts["year"]} renewal'
    else:
        heading = 'Our recommendation' if picked else 'At a glance'
    add('answer', heading, 'What we recommend, and what it costs' if picked else 'What we looked at', found)
    history = (answer.experience(facts) if on('experience') else []) + answer.markets(facts)
    add('history', 'How we got here', 'What we asked for and what came back', history)
    pages, named = [], []
    for line in facts['lines']:
        if not any(line['parts'].values()):
            continue  # the producer switched this whole line off
        found = line_pages.pages(line, facts, colours)
        if found:
            pages += found
            named.append(line['label'])
    add('coverage', 'Your coverage', ' · '.join(named), pages or coverage.nothing_to_compare(facts))
    after = closing.next_steps(facts) + (closing.calendar(facts) if on('calendar') else [])
    add('next', 'What happens next', 'Dates, and how we stay in touch', after)
    return sections, on


def story(facts):
    """[[flowable]]: the cover, then every page in order, ending with the important information."""
    colours = look.colours_of(facts)
    sections, on = _sections(facts, colours)
    pictures, draft = facts['pictures'], facts['draft']
    out = [opening.cover(facts)]
    framed = on('agenda') and len(sections) >= 3
    if framed:
        entries = [{'title': section['title'], 'sub': section['sub']} for section in sections]
        placed = furniture.agenda_items(entries, colours, draft=draft, picture=pictures.get('agenda'))
        out.append([flowables.FullPage(placed, ground=furniture.dark_ground(colours), title='Agenda')])
    for number, section in enumerate(sections, start=1):
        if framed:
            picture = pictures.get('sections')
            placed = furniture.section_items(
                number, section['title'], section['sub'], colours, draft=draft, picture=picture
            )
            ground = furniture.dark_ground(colours, mark=not picture)
            out.append([flowables.FullPage(placed, ground=ground, title=section['title'])])
        out += section['pages']
    out += closing.thank_you(facts)
    out += (firm.bios(facts) if on('bios') else []) + closing.important(facts)
    return out


def sections_of(facts):
    """The sections' keys and titles in order (what the agenda promises), for the ledger and tests."""
    sections, _on = _sections(facts, look.colours_of(facts))
    return [(section['key'], section['title']) for section in sections]
