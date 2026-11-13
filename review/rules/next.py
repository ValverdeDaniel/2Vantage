"""What to do next on a deal's requests (plan.md §5.8, §8.8; L3, L4, L14, L25, L119; old 891f1b3 `review/board.py`
`_next`). Pure: the facts in, the ranked entries out. The Board's Next banner, a section bar's Next line and the
request page's banner read the same ranking, and Agenda imports its predicates, so there is one rule (L119).

`rank(facts, now, surface=None)` → up to 8 entries {kind, label, why, fix, rank, …}, in this order (L4), ties in
the order they are listed:
0. a link running out within 2 days that nobody opened since our newest ask (`link_expiring`, `unopened`);
1. a client question waiting over 24 hours (`question`);
2. what blocks the market: intake questions required to market, required census values blank (`blocks_carrier`, the
   old kind), and once
   quotes are in on typed counts with no census on file, their census (Ch. 8);
3. other links running out within 2 days;
4. newer questions;
5. the oldest answer waiting for review (`oldest`), then 6. the client's files to check;
7. once quotes are in, the intake's required questions drop below the answers (B19).
`surface` (intake, census) keeps one section's part of it, in the same order (L14); documents ride with the intake.
Each entry names its `surface` ('' for a link, which belongs to every section), so a section bar can keep its own.

`facts`: {links [{link_id, request_id, name, days_left, sent, submitted, expired, unopened}], questions {surface:
(count, oldest datetime)}, intake_required (count), census_required (count), no_census (bool), quotes_in (bool),
answers {surface: (count, oldest datetime)}, files (count)}.
"""

from datetime import timedelta

from .policy import EXPIRING_DAYS

LIMIT = 8
QUESTION_WAITS = timedelta(hours=24)
SURFACE_WORDS = {
    'census': 'the census',
    'intake': 'the intake',
    'questionnaire': 'the questionnaire',
    'documents': 'the documents',
}


def plural(count, noun):
    return f'{count} {noun}{"" if count == 1 else "s"}'


def expiring(link):
    """A sent, unanswered link that still opens and runs out within EXPIRING_DAYS (Agenda reads the same rule)."""
    days = link.get('days_left')
    return (
        bool(link.get('sent'))
        and not link.get('submitted')
        and not link.get('expired')
        and days is not None
        and (days <= EXPIRING_DAYS)
    )


def question_waiting(oldest, now):
    """True once a client question has waited over 24 hours."""
    return oldest is not None and now - oldest > QUESTION_WAITS


def _fix(surface, view='request'):
    return {'tab': 'review', 'view': view, 'pane': surface if surface != 'documents' else 'documents'}


def _links(facts, here):
    out = []
    if not here('links'):
        return out
    for link in facts.get('links') or []:
        if not expiring(link):
            continue
        days = link['days_left']
        when = 'today' if days <= 0 else f'in {plural(days, "day")}'
        unopened = bool(link.get('unopened'))
        who = f'{link["name"]}’s link' if link.get('name') else 'The private link'
        out.append((0 if unopened else 3, {
            'kind': 'link_expiring',
            'surface': '',
            'label': f'{who} runs out {when}',
            'why': ('Not opened since the last ask. ' if unopened else '') + 'Extend it, or nudge them.',
            'unopened': unopened,
            'link_id': link['link_id'],
            'request_id': link['request_id'],
            'fix': {'tab': 'review', 'view': 'request'},
        }))  # fmt: skip
    return out


def _questions(facts, here, now):
    out = []
    for surface, (count, oldest) in (facts.get('questions') or {}).items():
        if not count or not here(surface):
            continue
        out.append((1 if question_waiting(oldest, now) else 4, {
            'kind': 'question',
            'surface': 'intake' if surface == 'documents' else surface,
            'label': f'{plural(count, "client question")} on {SURFACE_WORDS.get(surface, surface)}',
            'why': 'They are waiting on our answer.',
            'since': oldest.isoformat() if oldest else None,
            'fix': _fix(surface),
        }))  # fmt: skip
    return out


def _blocks(facts, here):
    out = []
    intake = facts.get('intake_required') or 0
    if intake and here('intake'):
        out.append((7 if facts.get('quotes_in') else 2, {
            'kind': 'blocks_carrier',
            'surface': 'intake',
            'label': f'{plural(intake, "intake question")} required to market',
            'why': 'Required before this goes to market.',
            'fix': {'tab': 'review', 'view': 'board', 'section': 'intake', 'lane': 'missing'},
        }))  # fmt: skip
    census = facts.get('census_required') or 0
    if census and here('census'):
        out.append((2, {
            'kind': 'blocks_carrier',
            'surface': 'census',
            'label': f'{plural(census, "required census value")} still blank',
            'why': 'The carriers’ files need them.',
            'fix': {'tab': 'review', 'view': 'board', 'section': 'census', 'lane': 'missing'},
        }))  # fmt: skip
    if facts.get('no_census') and facts.get('quotes_in') and here('census'):
        out.append((2, {
            'kind': 'blocks_carrier',
            'surface': 'census',
            'label': 'No census on file yet',
            'why': 'The quotes run on typed counts: ask for their census file.',
            'fix': {'tab': 'review', 'view': 'board', 'section': 'census', 'lane': 'missing'},
        }))  # fmt: skip
    return out


def _waiting(facts, here):
    out = []
    for surface, (count, oldest) in (facts.get('answers') or {}).items():
        if count and here(surface):
            out.append((5, {
                'kind': 'oldest',
                'surface': surface,
                'label': f'{plural(count, "answer")} from the client on {SURFACE_WORDS.get(surface, surface)}',
                'why': 'Waiting longest for review.',
                'since': oldest.isoformat() if oldest else None,
                'fix': {'tab': 'review', 'view': 'queue', 'section': surface},
            }))  # fmt: skip
    files = facts.get('files') or 0
    if files and here('documents'):
        out.append((6, {
            'kind': 'oldest',
            'surface': 'intake',
            'label': f'{plural(files, "file")} from the client to check',
            'why': 'Accept it, or say it is the wrong one.',
            'fix': {'tab': 'documents'},
        }))  # fmt: skip
    return out


def rank(facts, now, surface=None):
    def here(name):
        if surface is None or name == 'links':
            return True
        return name == surface or (surface == 'intake' and name == 'documents')

    ranked = [*_links(facts, here), *_questions(facts, here, now), *_blocks(facts, here), *_waiting(facts, here)]
    ranked.sort(key=lambda entry: entry[0])
    return [{**entry, 'rank': at} for at, entry in ranked][:LIMIT]
