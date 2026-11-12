"""Matching a file's people to the roster (plan.md §5.3.2 step 7; C17, L112). Pure.

Ported from old Vantage 891f1b3 `market/census_upsert.py` (`upsert_roster`'s matching and its keep rule):
- an employee matches by the employer's id, else SSN digits, else last name + first name + date of birth, strongest
  first; an identity two people share identifies nobody. Live people first; a removed one comes back by identity;
- a dependent matches only inside its matched employee's family: SSN, else name + date of birth, else relationship and
  order;
- on a matched person, a value the file states differently replaces the stored one only when the stored one came from
  a file (origin import or ai); what a person entered (typed, relayed, a client's approved answer) stays; an equal
  value changes nothing; a blank in the file keeps the stored value;
- unmatched incoming people are added; live people missing from the file are removed softly with their dependents,
  except someone a person worked on (a typed, relayed or client value, a client entry, or added through a link), who
  is kept and reported — and an employee whose dependent is kept stays too.
A roster entry: {id, kind, employee_id, position, values, sources, client, added_by_link, removed}.
"""

from collections import namedtuple

from .fields import DEPENDENT, EMPLOYEE
from .importer.people import identities
from .values import digits

FROM_A_FILE = ('import', 'ai')
WORK = ('typed', 'relay', 'client')

# matched {index: member id}; restored {member ids}; changes {index: {key: value}}; created [indexes];
# removed / kept [member ids]; why {member id: words}.
Match = namedtuple('Match', 'matched restored changes created removed kept why')


def dependent_identities(values, order):
    out = []
    ssn = digits(values.get('ssn'))
    if len(ssn) >= 4:
        out.append(f'S{ssn}')
    name = '|'.join(' '.join(str(values.get(key) or '').lower().split()) for key in ('last_name', 'first_name', 'dob'))
    if name.strip('|'):
        out.append(f'N{name}')
    out.append(f'R{" ".join(str(values.get("relationship") or "").lower().split())}#{order}')
    return out


def _index(candidates):
    """{identity: member id} over (id, identities); an identity two people share maps to None."""
    index = {}
    for member_id, found in candidates:
        for identity in found:
            if identity in index and index[identity] != member_id:
                index[identity] = None
            else:
                index.setdefault(identity, member_id)
    return index


def _match(index, found, taken):
    for identity in found:
        member_id = index.get(identity)
        if member_id is not None and member_id not in taken:
            return member_id
    return None


def _match_employees(people, roster, taken):
    matched = {}
    for removed in (False, True):  # the live roster first; a removed person comes back by identity
        pool = [m for m in roster if m['kind'] == EMPLOYEE and m['removed'] == removed]
        index = _index((m['id'], identities(m['values'])) for m in pool)
        for i, person in enumerate(people):
            if person['kind'] != EMPLOYEE or i in matched:
                continue
            member_id = _match(index, identities(person['values']), taken)
            if member_id is not None:
                taken.add(member_id)
                matched[i] = member_id
    return matched


def _match_dependents(people, roster, matched, taken):
    families = {}
    for member in sorted(roster, key=lambda m: (m['position'], m['id'])):
        if member['kind'] == DEPENDENT and member['employee_id']:
            families.setdefault(member['employee_id'], []).append(member)
    seen = {}
    found = {}
    for i, person in enumerate(people):
        employee = matched.get(person['parent']) if person['kind'] == DEPENDENT else None
        if employee is None:
            continue
        order = seen[person['parent']] = seen.get(person['parent'], -1) + 1
        for removed in (False, True):
            siblings = [m for m in families.get(employee, []) if m['removed'] == removed]
            index = _index((m['id'], dependent_identities(m['values'], k)) for k, m in enumerate(siblings))
            member_id = _match(index, dependent_identities(person['values'], order), taken)
            if member_id is not None:
                taken.add(member_id)
                found[i] = member_id
                break
    return found


def changes_for(values, sources, incoming):
    """The keys a file may change on a matched person, {key: value} (the keep rule above)."""
    out = {}
    for key, value in incoming.items():
        stored = values.get(key)
        if not value or value == stored:
            continue
        if stored in (None, '') or (sources.get(key) or {}).get('origin') in FROM_A_FILE:
            out[key] = value
    return out


def worked_on(member):
    """Words for why a person a file no longer lists is kept, or '' when nobody worked on them."""
    if member.get('added_by_link'):
        return 'added through a client link'
    if member.get('client'):
        return 'has client answers'
    origins = {(entry or {}).get('origin') for entry in (member.get('sources') or {}).values()}
    if origins & set(WORK):
        return 'has values a person entered'
    return ''


def _leftovers(roster, taken):
    """(removed ids, kept ids, why) for the live people the file no longer lists."""
    left = [m for m in roster if not m['removed'] and m['id'] not in taken]
    why = {m['id']: worked_on(m) for m in left}
    kept = {member_id for member_id, words in why.items() if words}
    for member in left:  # an employee whose kept dependent still hangs on them stays
        if member['kind'] == DEPENDENT and member['id'] in kept and member['employee_id'] in why:
            if member['employee_id'] not in kept:
                kept.add(member['employee_id'])
                why[member['employee_id']] = 'a dependent is kept'
    removed = [m['id'] for m in left if m['id'] not in kept]
    kept_ids = [m['id'] for m in left if m['id'] in kept]
    return removed, kept_ids, {member_id: why[member_id] for member_id in kept_ids}


def match(people, roster):
    """How a file's `people` (importer.people.build) land on the `roster`."""
    taken = set()
    matched = _match_employees(people, roster, taken)
    matched.update(_match_dependents(people, roster, matched, taken))
    by_id = {member['id']: member for member in roster}
    changes = {i: changes_for(by_id[m]['values'], by_id[m]['sources'], people[i]['values']) for i, m in matched.items()}
    restored = {member_id for member_id in matched.values() if by_id[member_id]['removed']}
    created = [i for i in range(len(people)) if i not in matched]
    removed, kept, why = _leftovers(roster, taken)
    return Match(matched, restored, changes, created, removed, kept, why)
