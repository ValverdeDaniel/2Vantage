"""Writing a matched file onto the roster (plan.md §5.3.2 steps 6–8; C16, C17, L112).

`write` lands `census.matching.match`'s answer on the locked people: matched people take the file's values through
`deals.values.apply` (origin `import`, the document and the sheet cell; `low` when the column was mapped with low
confidence; a roster Claude read: origin `ai`, the file and page, `low` where Claude was unsure) and their place in
the file; a removed person who comes back is restored; new people are created,
employees before their dependents; people the file no longer lists are removed softly unless someone worked on them,
who are kept after the file's people. A person nothing changed for is not written at all. Returns the Activity
entries (keys only) and the counts.
"""

from collections import namedtuple

from deals import clock
from deals.activity import change
from deals.values import apply, source

from ..fields import DEPENDENT, EMPLOYEE
from ..models import Member
from .rows import target

LOW = 'mapping'  # `low` on a value whose column was mapped with low confidence (§5.3.2 step 4)
UNSURE = 'Claude was not sure of this value.'  # `low` on a value a census read doubted (slice 51)
SAVED = ['values', 'sources', 'position', 'kind', 'employee', 'removed_at', 'updated_at']

Written = namedtuple('Written', 'changes stats')


def _place(member):
    return (member.position, member.kind, member.employee_id, member.removed_at)


def _linked(person):
    return person['kind'] == DEPENDENT and person['parent'] is not None


def _create(deal_id, people, indexes, placed, sources_for):
    """New people, employees (and unlinked dependents) first: their dependents need their ids."""
    created = []
    for wave in (False, True):
        new = []
        for index in indexes:
            person = people[index]
            if _linked(person) != wave:
                continue
            member = Member(deal_id=deal_id, kind=person['kind'], position=index, values={}, sources={})
            apply(member.values, member.sources, person['values'], sources_for(person))
            member.employee = placed[person['parent']] if wave else None
            placed[index] = member
            new.append(member)
        created += Member.all_objects.bulk_create(new)
    return created


def write(user, deal_id, document_id, people, found, members):
    """Land `people` (importer.people.build) on the locked `members` as `found` (matching.Match) says."""
    now = clock.now()
    by_id = {member.id: member for member in members}
    placed, keys, before = {}, {}, {}

    def sources_for(person):
        if 'pages' in person:  # a roster Claude read (census.reader.staged, slice 51): its file and page, its doubt
            return lambda key: source(
                'ai',
                user,
                doc=person.get('doc') or document_id,
                page=person['pages'].get(key),
                low=UNSURE if key in person['low'] else None,
            )
        return lambda key: source(
            'import',
            user,
            doc=document_id,
            cell=person['cells'].get(key),
            low=LOW if key in person['low'] else None,
        )

    for index, member_id in found.matched.items():
        member, person = by_id[member_id], people[index]
        before[member_id] = _place(member)
        keys[member_id] = set(apply(member.values, member.sources, found.changes[index], sources_for(person)))
        if member.removed_at is not None:
            member.removed_at = None
            keys[member_id].add('removed_at')
        member.position, member.kind = index, person['kind']
        placed[index] = member
    created = _create(deal_id, people, found.created, placed, sources_for)
    for index, member_id in found.matched.items():  # a matched dependent sits under its employee in the file
        person = people[index]
        by_id[member_id].employee = placed[person['parent']] if _linked(person) else None
    changed = [by_id[m] for m in found.matched.values() if keys[m] or _place(by_id[m]) != before[m]]
    entries = [change(target(member.id), sorted(keys[member.id])) for member in changed if keys[member.id]]
    entries += [change(target(member.id), sorted(member.values)) for member in created]
    for member_id in found.removed:
        by_id[member_id].removed_at = now
        changed.append(by_id[member_id])
        entries.append(change(target(member_id), ['removed_at']))
    for offset, member_id in enumerate(found.kept, start=len(people)):
        if by_id[member_id].position != offset:
            by_id[member_id].position = offset
            changed.append(by_id[member_id])
    for member in changed:
        member.updated_at = now
    Member.all_objects.bulk_update(changed, SAVED)
    stats = {
        'rows': len(people),
        'employees': sum(1 for person in people if person['kind'] == EMPLOYEE),
        'dependents': sum(1 for person in people if person['kind'] == DEPENDENT),
        'created': len(created),
        'updated': sum(1 for index in found.matched if found.changes[index]),
        'restored': len(found.restored),
        'removed': len(found.removed),
        'kept': len(found.kept),
    }
    return Written(entries, stats)
