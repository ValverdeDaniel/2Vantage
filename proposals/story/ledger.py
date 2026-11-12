"""The page ledger: what the Presentation format would print for this deal, page by page, and why a page would not
(plan.md §8.14; J42; old Vantage 891f1b3 `views/presentation_pages.page_ledger`, the `wwc4` review of 2026-11-04). Pure.

A ledger, never a gate: a page with nothing to say does not print, and nothing here stops a download. Each row is
{key, label, switchable, ready, why, fix}: `ready` is whether the page has its facts (None where only the story can
tell), `why` what is missing when it has not, and `fix` where to put it right, in the shape of a check's Fix ▸
({card} or {tab}, or {drawer: 'firm'} for the Firm pages drawer; None while that place does not exist). The
switches are the card's own (`output.pages`); the ledger never reads them, so a toggle needs no re-read.

The firm's pages (About, the team, the calendar, bios) read from FirmPages and the team (`firm_read.ledger`); their
Fix ▸ opens the Firm pages drawer (slice 34, J155). Renewal history waits with past plan years (J44, deferred).
"""

FIRM = {'drawer': 'firm'}


def _row(key, label, ready, why='', switchable=True, card=None, fix=None):
    fix = fix or ({'card': card} if card else None)
    return {
        'key': key,
        'label': label,
        'switchable': switchable,
        'ready': ready,
        'why': '' if ready else why,
        'fix': fix if ready is False else None,
    }


def rows(*, renewal, recommended, negotiated, experience, next_steps, firm=None):
    """The ledger in the story's order. `renewal`: the deal is a renewal (`deals.rules.deal_type`); `recommended`:
    every line has its recommendation (`ready.ok`), which the at-a-glance page needs; `negotiated`: a first offer is
    on the proposal (a priced version of a quote); `experience`: config.experience; `next_steps`: config.next_steps;
    `firm`: {about, calendar, team: [{bio}]} (`firm_read.ledger`; None reads as nothing written)."""
    firm = firm or {}
    team = firm.get('team') or []
    told = bool((experience.get('summary') or '').strip() or experience.get('rows'))
    return [
        _row('agenda', 'Agenda and section pages', None, 'prints with three or more sections'),
        _row('about', 'About the firm', bool(firm.get('about')), "the firm's story is not written yet", fix=FIRM),
        _row('team', 'Your team', bool(team), 'nobody on the team yet', fix=FIRM),
        _row(
            'overview',
            'Renewal overview' if renewal else 'Recommendation at a glance',
            recommended,
            "needs a recommended plan on every line, and each current plan's enrollment where a line has several",
            switchable=False,
            card='quotes',
        ),
        _row(
            'negotiation',
            'What we negotiated',
            negotiated,
            "needs the carrier's first offer: a negotiated version of the renewal, or the renewal letter's %",
            switchable=False,
            card='quotes',
        ),
        _row('experience', 'Plan experience', told, 'nothing typed yet', card='pages'),
        _row('next_steps', 'Next steps', bool(next_steps), 'no next steps yet', switchable=False, card='next_steps'),
        _row('calendar', 'Meeting calendar', bool(firm.get('calendar')), 'no meeting calendar yet', fix=FIRM),
        _row(
            'bios',
            'Team bios',
            any((member.get('bio') or '').strip() for member in team),
            'no bios written yet',
            fix=FIRM,
        ),
    ]
