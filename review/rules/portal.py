"""The client portal's own rules (plan.md §5.8, §8.20; L81, L83, L103; B43). Pure: payload pieces in, answers out.

- `editable(source, value, reopened=False)`: B43's one lock rule. An answer a person typed, entered for the client,
  approved, or a client answer a person approved, is on file: the portal shows it "Already on file ✓" and takes no
  answer for it, unless a person sent it back (`reopened`, slice 56). A value Claude or an import put there, with no
  person's approval, is the client's to correct (`we_read`).
- `form_stamp(link, request, now, notes='')`: one opaque word for what the page was built from (L103, Ch. 15): the
  request's `form_version`, the link's blank flag, submitted, security and PIN version, closed and turned off, and
  (slice 56) its notes' stamp, so a reply or a send-back of ours shows on a page left open. A poll that reads a
  different word re-reads the page and keeps what the person typed.
- `rail(intake, people, census_file, documents, follow_ups)`: the to-do list (L81, old `_client_checklist`): a row per
  section, its counts and whether it is done, and (slice 56) Follow-ups: what we sent back or asked again, done once
  they answered it; the browser recounts the form's rows from what is typed, with the same rule (portalModel.js).
"""

import hashlib

LOCKING_ORIGINS = ('typed', 'relay', 'client', 'agency')
READ_ORIGINS = ('ai',)


def blank(value):
    return value in (None, '', [])


def editable(source, value, reopened=False):
    if reopened or blank(value) or not isinstance(source, dict):
        return True
    return source.get('origin') not in LOCKING_ORIGINS and not source.get('confirmed')


def we_read(source, value):
    """'read' for an answer Claude read and no person approved: the portal asks the client to correct it (L83)."""
    if blank(value) or not isinstance(source, dict):
        return ''
    return 'read' if source.get('origin') in READ_ORIGINS and not source.get('confirmed') else ''


def form_stamp(link, request, now, notes=''):
    parts = [
        notes,
        request.form_version,
        int(link.blank),
        link.security,
        link.pin_version,
        link.submitted_at.isoformat() if link.submitted_at else '',
        request.closed_at.isoformat() if request.closed_at else '',
        link.revoked_at.isoformat() if link.revoked_at else '',
        link.expires_at > now,
    ]
    return hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:16]


def _counted(fields):
    total = len(fields)
    filled = sum(1 for field in fields if not blank(field.get('value')) or field.get('locked'))
    return filled, total


def rail(words, intake, people, census_file, documents, follow_ups=()):
    """{items: [{key, kind, label, done, filled?, total?}], done, total}. `words` holds the labels; `intake` is the
    intake section (or None), `people` the people asked, `census_file` its section (or None), `documents` the slots,
    `follow_ups` the follow-up cards."""
    items = []
    if intake:
        shown = [field for section in intake['sections'] for field in section['fields'] if field['shown']]
        if shown:
            filled, total = _counted(shown)
            items.append({'key': 'intake', 'kind': 'fields', 'label': words['intake'], 'filled': filled,
                          'total': total, 'done': filled >= total})  # fmt: skip
    cells = [field for person in people for field in person['fields']]
    if cells:
        filled, total = _counted(cells)
        items.append({'key': 'people', 'kind': 'fields', 'label': words['people'], 'filled': filled, 'total': total,
                      'done': filled >= total})  # fmt: skip
    if census_file is not None:
        items.append({'key': 'census', 'kind': 'census_upload', 'label': words['census'],
                      'done': bool(census_file['received'])})  # fmt: skip
    for slot in documents:
        items.append({'key': f'doc_{slot["slot"]}', 'kind': 'document', 'label': slot['label'],
                      'done': bool(slot['received'])})  # fmt: skip
    asked = [card for card in follow_ups if card['needs_answer'] or card['answered']]
    if asked:
        filled = sum(1 for card in asked if not card['needs_answer'])
        items.append({'key': 'followups', 'kind': 'fields', 'label': words['followups'], 'filled': filled,
                      'total': len(asked), 'done': filled >= len(asked)})  # fmt: skip
    done = sum(1 for item in items if item['done'])
    return {'items': items, 'done': done, 'total': len(items)}
