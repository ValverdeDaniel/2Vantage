"""Review's lines in rfp's export check (plan.md §8.12; L120, OQ85; old 891f1b3 `export_check.deal_problems`; slice 55),
registered in ReviewConfig.ready() with `rfp.check.providers.register`.

What the client sent on the census and nobody approved yet never prints (OQ85), so a census file leaves it out; the
check says so, as counts, never a value or a name:
- `client_waiting`: answers (and people a client added) ready for review — "not in the file until approved";
- `client_typing`: answers still being typed on a link (not submitted yet, not idle a day);
- `going_back`: answers sent back to the client and not answered yet (the notes, slice 56; none before).
The client's questions on a questionnaire are that form's own check (`questionnaire.check`). Fix ▸ opens the review
queue (the census's section first when it holds something).

`stamp(deal)` is the lines' counts, so `checks_stamp` moves when one does (an answer saved, a link submitted, an
answer turning idle) and the page asks for the pills again.
"""

from deals import clock
from rfp.check.problems import plural, problem

from .models import ReviewNote
from .rules import sections as section_rules
from .selectors import entries as entry_rows

FIX = {'tab': 'review', 'view': 'queue'}


def _census(deal):
    found = entry_rows.waiting([deal.id], ('census',)).get(deal.id, [])
    return found, entry_rows.links_of(found)


def problems(deal):
    found, links = _census(deal)
    counts = section_rules.counts(found, links, clock.now())['census']
    out = []
    waiting, typing = counts['to_review'], counts['in_progress']
    if waiting:
        text = (
            f'{waiting} census {plural(waiting, "answer", "answers")} the client sent '
            f'{plural(waiting, "is", "are")} waiting for review — not in the file until approved.'
        )
        out.append(problem('client_waiting', text, waiting, fix=FIX))
    if typing:
        text = (
            f'The client is still answering {typing} census {plural(typing, "value", "values")} (not submitted yet) — '
            'not in the file until approved.'
        )
        out.append(problem('client_typing', text, typing, fix=FIX))
    back = ReviewNote.objects.filter(
        deal_id=deal.id, surface='census', kind='sendback', resolved_at__isnull=True
    ).count()
    if back:
        text = (
            f'{back} census {plural(back, "value", "values")} went back to the client and '
            f'{plural(back, "is", "are")} not answered yet.'
        )
        out.append(problem('going_back', text, back, fix=FIX))
    return out


def stamp(deal):
    found, links = _census(deal)
    counts = section_rules.counts(found, links, clock.now())['census']
    back = ReviewNote.objects.filter(deal_id=deal.id, surface='census', kind='sendback', resolved_at__isnull=True)
    return [counts['to_review'], counts['in_progress'], back.count()]
