"""intake's half of Work with Claude's chat (plan.md §10.6, §4.5 †; D98, F111, O.6 #16; slice 24).

- `update_client_guidance`: Claude restates the client guidance whole, as a short list, when the producer says what
  the client wants. It writes nothing: the item lands through `update_answers` (the guidance is intake's
  `client_guidance` answer, at most 4,000 characters, the one cleaner checks it) when the turn ends or the producer
  applies it, recorded as Claude's so ↶ Undo this run puts the guidance back.
- The context provider tells a turn the client's goals (the Goals card's answers) and the guidance, in <guidance>.
The drawer's GuidanceBox writes the same answer through `PATCH deals/{id}/intake/` (D6, D98). The intake turn's
answers and coverage lines (`turn_intake`, B39; slice 51) land through this owner too.
"""

from ai import tools
from ai.registry import Tool

from . import form
from .models import Intake
from .services.answers import update_answers

SAME = 'That is the client guidance already, so nothing changes.'
LANDS = 'It changes when your turn ends; the producer can undo it.'
WAITS = 'It waits for the producer to review and apply it.'


def _answers(deal):
    row = Intake.objects.filter(deal=deal).only('answers').first()
    return dict(row.answers) if row else {}


def provide(deal, page):
    """<guidance>: the client's goals and the guidance as they stand ('' when none is written)."""
    answers = _answers(deal)
    goals = [
        f'- {question["label"]}: {" ".join(str(answers[question["key"]]).split())}'
        for question in form.QUESTIONS
        if question['section'] == 'goals' and str(answers.get(question['key']) or '').strip()
    ]
    guidance = str(answers.get(form.GUIDANCE) or '').strip()
    if not goals and not guidance:
        return '<guidance>\n(no client guidance yet)\n</guidance>'
    parts = (['Goals the producer recorded:', *goals] if goals else []) + (
        [f'Client guidance:\n{guidance}'] if guidance else ['Client guidance: none yet.']
    )
    return '<guidance>\n' + '\n'.join(parts) + '\n</guidance>'


def update_client_guidance(turn, data):
    text = tools.text(data.get('text'), 'The guidance', form.GUIDANCE_LIMIT)
    old = str(_answers(turn.deal).get(form.GUIDANCE) or '')
    if text.strip() == old.strip():
        return SAME
    staged = turn.staged('intake', 'guidance')
    if staged:
        staged[0]['new'] = text
    else:
        turn.add({'owner': 'intake', 'op': 'guidance', 'old': old, 'new': text, 'label': 'Update the client guidance'})
    return f'Proposed the new client guidance. {LANDS if turn.lands else WAITS}'


def apply(user, deal, job, items):
    """Intake's turn owner: the guidance through the form's one writer, as Claude's change; answers and coverage lines
    (`turn_intake`, B39; slice 51) through the intake reader's landing, in Claude's own row."""
    ids, said, skipped = [], [], []
    guidance = [item for item in items if item['op'] == 'guidance']
    if guidance:
        answered = update_answers(user, deal.id, {form.GUIDANCE: guidance[-1]['new']}, by_claude=True)
        if answered.activity is not None:
            ids.append(answered.activity.id)
            said.append('updated the client guidance')
    others = [item for item in items if item['op'] in ('answer', 'coverage')]
    if others:
        from .services.read_apply import land

        row, parts, skipped = land(user, deal, others, by_claude=True)
        if row is not None:
            ids.append(row.id)
            said.append('set ' + ', '.join(parts))
    if not ids:
        return {'activity_ids': [], 'summary': '', 'areas': [], 'skipped': skipped}
    return {'activity_ids': ids, 'summary': '; '.join(said), 'areas': ['intake', 'activity'], 'skipped': skipped}


TOOL = Tool(
    name='update_client_guidance',
    owner='intake',
    order=50,
    description=(
        'Replace the client guidance with its complete current version: what the client wants (budget, networks, '
        'lines, deductible or benefit levels, carriers) as a short bullet list, restating everything that still '
        'applies. At most 4,000 characters.'
    ),
    schema=tools.schema({'text': {'type': 'string'}}),
    run=update_client_guidance,
)


def register():
    from django.conf import settings

    from ai import registry

    from . import turn_intake

    registry.register_tool(TOOL)
    registry.register_context('guidance', provide, order=10)
    registry.register_turn_owner('intake', apply, order=10)
    if settings.AI_PHI_READERS:  # B39 (slice 51): with the intake reader, behind the PHI-gate switch (§10.8)
        registry.register_tool(turn_intake.TOOL)
        registry.register_context('intake', turn_intake.provide, order=12)
