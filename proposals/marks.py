"""The builder's completed marks (plan.md §8.14; J18, J19; D-113; ported from old Vantage 891f1b3
`pipeline/proposal_review.py`). Pure.

"I reviewed this card, it is what I want": a completed card starts collapsed for everyone on the deal. Marks are
stored apart from what prints (`ProposalConfig.marks`): {card: {by, at}, lines: {line: {card: {by, at}}}}. An edit
clears the mark of the card it belongs to (`config.card_of`); a plan write clears the line's Plans card (quotes'
`plans_changed`). A mark is the path "marks.<card>" or "marks.lines.<line>.<card>" in Activity.
"""

from . import catalog

NO_CARD = 'There is no builder card called "{card}".'


def path(card, line=None):
    return f'marks.lines.{line}.{card}' if line else f'marks.{card}'


def stamp_of(marks, card, line=None):
    """A card's {by, at}, or None."""
    if line:
        return ((marks.get('lines') or {}).get(line) or {}).get(card) or None
    return marks.get(card) or None


def stamp(user, at):
    name = (user.get_full_name() or '').strip() if user else ''
    return {'by': name or getattr(user, 'username', ''), 'at': at}


def counted(proposal_lines):
    """The (card, line) pairs that count toward "the proposal is built": the cards on screen, each line card once per
    line on the proposal. The optional cards never count."""
    deal = [(card, None) for card in catalog.DEAL_CARDS if card in catalog.ON_SCREEN]
    per_line = [(card, line) for line in proposal_lines for card in catalog.LINE_CARDS if card in catalog.ON_SCREEN]
    return deal + per_line


def done(marks, proposal_lines):
    """{done, total} over the counted cards."""
    cards = counted(proposal_lines)
    return {'done': sum(1 for card, line in cards if stamp_of(marks, card, line)), 'total': len(cards)}


def line_done(marks, line):
    """Every line card on screen marked for this line (the line tab's ✓, J31)."""
    return all(stamp_of(marks, card, line) for card in catalog.LINE_CARDS if card in catalog.ON_SCREEN)


def cleared_by(marks, owners):
    """The mark paths an edit to `owners` ((card, line) pairs, from `config.card_of`) takes off: only marks that
    exist."""
    return sorted({path(card, line) for card, line in owners if stamp_of(marks, card, line)})
