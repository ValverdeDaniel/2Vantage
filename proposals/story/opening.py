"""The cover (plan.md §9.5; J123; old Vantage 891f1b3 `proposal_presentation.cover_flowable`). Pure.

The client's name is the hero on the dark ground, the firm's logo above it; under the rule what the document is (the
producer's own title, else "2027 Benefits Renewal" or "… Proposal"), then when coverage starts and who prepared it
and when ("Prepared by" is the agent-name rule: the agent of record, else the deal's owner, else the agency's
producer; OQ41). The stock picture stands in its frame (J35's default until slice 34's Pictures card); Draft until
the proposal is issued (OQ35). A Classic cover (white) waits with Classic (J143).
"""

from ..layout import flowables, furniture
from . import look


def cover(facts):
    colours = look.colours_of(facts)
    client = facts['client']
    kind = facts['kind'] or 'Employee Benefits Proposal'
    own = facts['title']
    if own and own != f'{client} — Employee Benefits Proposal':
        kind = own
    lines = []
    effective = look.long_date(facts['effective'])
    if effective:
        lines.append(f'Coverage effective {effective}')
    prepared = look.long_date(facts['prepared_on'])
    author = facts['prepared_by']
    if prepared or author:
        lines.append(
            ' '.join(
                bit
                for bit in (f'Prepared {prepared}' if prepared else 'Prepared', f'by {author}' if author else '')
                if bit
            )
        )
    picture = facts['pictures'].get('cover')
    placed = furniture.cover_items(
        {'client': client, 'kind': kind, 'lines': lines},
        colours,
        logo_src=facts['agency']['logo'],
        picture=picture,
        draft=facts['draft'],
    )
    return [flowables.FullPage(placed, ground=furniture.dark_ground(colours, mark=not picture), title=client)]
