"""What the client's open requests asked for (I45, I.5 bug 6), read from each request's stored asks (plan.md §6.12
`ClientRequest.asks`). Pure. "Waiting on the client" for a census, the BOR, the checklist's files or the questionnaire
only when an ask that went out named them; a draft nobody sent waits on us, not the client.

Also the old `_ask_words` (891f1b3 `tasks/steps.py`): what one request asked, in a producer's words ("census
request", "census and intake answers request").
"""


def _census(asks):
    census = asks.get('census') or {}
    return census.get('scope', 'none') != 'none' or bool(census.get('file')) or bool(census.get('cells'))


def _intake(asks):
    intake = asks.get('intake') or {}
    blocks = [block for block in intake.get('blocks') or [] if block != 'files']
    return bool(intake.get('scope') or intake.get('keys') or blocks)


def _documents(asks):
    documents = asks.get('documents') or {}
    intake = asks.get('intake') or {}
    return bool(documents.get('slots') or documents.get('missing') or 'files' in (intake.get('blocks') or []))


def _slots(asks):
    return [slot.partition('@')[0] for slot in (asks.get('documents') or {}).get('slots') or []]


def census_file(asks_list):
    """An ask out for the census (the file, or census values)."""
    return any(_census(asks) for asks in asks_list)


def bor(asks_list):
    """An ask out for the BOR: the intake's BOR block, or the signed file."""
    return any('bor' in ((asks.get('intake') or {}).get('blocks') or []) or 'bor' in _slots(asks) for asks in asks_list)


def files(asks_list, kinds):
    """An ask out for any of these checklist files (by kind), or for every missing file."""
    wanted = set(kinds)
    for asks in asks_list:
        documents = asks.get('documents') or {}
        if documents.get('missing') or 'files' in ((asks.get('intake') or {}).get('blocks') or []):
            return True
        if wanted & set(_slots(asks)):
            return True
    return False


def questionnaire(asks_list):
    """An ask out for the medical questionnaire: the form online or as an upload, or its file."""
    return any(asks.get('questionnaires') or 'questionnaire' in _slots(asks) for asks in asks_list)


def words(asks):
    """What one request asked, in a producer's words (old `_ask_words`)."""
    asks = asks or {}
    found = []
    if _census(asks):
        found.append('census')
    if _intake(asks):
        found.append('intake answers')
    if _documents(asks):
        found.append('documents')
    if asks.get('questionnaires'):
        found.append('questionnaire')
    if not found:
        return 'request'
    if len(found) == 1:
        return f'{found[0]} request'
    return f'{", ".join(found[:-1])} and {found[-1]} request'
