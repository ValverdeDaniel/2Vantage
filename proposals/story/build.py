"""The client deck of a deal, laid out once (plan.md §9.5; J122): Facts (`facts.facts`) → the story
(`sequence.story`) → the one layout pass (`layout.record.lay_out`) → recorded pages, which the PDF draws
(`paint.pdf.draw`, slice 29) and the PowerPoint replays (`paint/pptx/`, slice 31). Writes nothing.

`deck(deal)` → {title, pages, sources}: `pages` as `record.lay_out` gives them; `sources` the bytes of the pictures
that are not bundled (the firm's logo, the team's photos), by the names the frames use.
"""

from ..layout import record, tokens
from . import facts as client_facts
from . import look, sequence


def chrome_of(found):
    """The footer's facts: "<client> · Prepared <date> · Version <n>", the rates note, the firm, its logo, Draft."""
    prepared = look.long_date(found['prepared_on'])
    stamp = [found['client'], f'Prepared {prepared}' if prepared else '']
    if found['version']:
        stamp.append(f'Version {found["version"]}')
    return {
        'stamp': ' · '.join(bit for bit in stamp if bit),
        'note': tokens.DISCLAIMER,
        'firm': found['agency']['name'],
        'logo': found['agency']['logo'],
        'draft': found['draft'],
        'colours': look.colours_of(found),
    }


def lay_out(found):
    """The recorded pages of a Facts."""
    return record.lay_out(sequence.story(found), chrome_of(found))


def deck(deal):
    found = client_facts.facts(deal)
    return {
        'title': f'{found["client"]} — Employee Benefits Proposal',
        'pages': lay_out(found),
        'sources': found['sources'],
    }


def file_name(deal):
    return f'{deal.client.name} - Proposal.pdf'
