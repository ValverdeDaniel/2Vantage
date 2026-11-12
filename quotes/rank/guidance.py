"""The client guidance Rank reads (plan.md §4.5 †, §10.4; D98, F111, O.6 #16; slice 37).

It is intake's `client_guidance` answer (what the client wants, in free text), read with the goals the producer
recorded in the Goals card, in the very block a chat turn reads (`intake.turn.provide`). Rank needs the guidance
itself: without it Rank is refused with "Add client guidance first" (F111; the old "Add client guidance before
ranking"). quotes sits right of intake in the chain, so it reads intake directly.
"""

from ai.progress import JobFailed
from intake import form
from intake import turn as intake_turn
from intake.models import Intake

NO_GUIDANCE = (
    'Add client guidance first: tell Claude what the client wants (budget, networks, deductible or benefit levels), '
    'or ✎ Edit the guidance in Work with Claude.'
)


def written(deal):
    """The guidance as written ('' when there is none)."""
    row = Intake.objects.filter(deal=deal).only('answers').first()
    return str(((row.answers or {}) if row else {}).get(form.GUIDANCE) or '').strip()


def block(deal):
    """The <guidance> block Claude reads; JobFailed with NO_GUIDANCE when the guidance is empty."""
    if not written(deal):
        raise JobFailed(NO_GUIDANCE)
    return intake_turn.provide(deal, {})
