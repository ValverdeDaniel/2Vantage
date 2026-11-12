"""Who a new request goes to (plan.md §5.8; L56, L57; Ch. 7): the client's contacts and people typed in, a link each.

`resolve(client_id, raw)` reads `[{contact_id} | {name, email?}]` and returns [Person(contact, name, email)], one per
person, de-duplicated: a contact picked twice, or a typed address that is already a contact's (it becomes that
contact, as the old `resolve_recipients` did). A name is enough while copying the link is the send (OQ82): the address
is optional, for the person's own record. Nobody named is a private link anyone holding it can open (L57). At most 20.
"""

from collections import namedtuple

from rest_framework.exceptions import ValidationError

from deals import contacts
from deals.models import Contact
from deals.services.contacts import EMAIL

from .. import words
from ..rules import policy

Person = namedtuple('Person', 'contact name email')


def _contact_person(contact):
    name = contact.name or contact.email or contacts.label(contact.role)
    return Person(contact, name[: contacts.LIMITS['name']], contact.email.strip())


def _typed(entry, by_email, errors):
    name = ' '.join(str(entry.get('name') or '').split())
    email = str(entry.get('email') or '').strip()
    if not name:
        errors.append(words.NAME_NEEDED)
    elif len(name) > contacts.LIMITS['name']:
        errors.append(f'Keep a name under {contacts.LIMITS["name"]} characters.')
    if email and (len(email) > contacts.LIMITS['email'] or not EMAIL.fullmatch(email)):
        errors.append(words.NOT_AN_EMAIL.format(value=f'"{email}"'))
    return Person(by_email.get(email.lower()) if email else None, name, email)


def _one(entry, known, by_email, errors):
    if not isinstance(entry, dict):
        errors.append(words.BAD_PERSON)
        return None
    if 'contact_id' not in entry:
        return _typed(entry, by_email, errors)
    try:
        contact = known.get(int(entry['contact_id']))
    except (TypeError, ValueError):
        contact = None
    if contact is None:
        errors.append(words.NOT_A_CONTACT.format(value=f'"{entry["contact_id"]}"'))
        return None
    return _contact_person(contact)


def resolve(client_id, raw):
    """[Person], in the order sent. Raises ValidationError {'people': [sentence]}."""
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise ValidationError({'people': [words.BAD_PERSON]})
    known = {contact.id: contact for contact in Contact.objects.filter(client_id=client_id)}
    by_email = {contact.email.strip().lower(): contact for contact in known.values() if contact.email.strip()}
    out, seen, errors = [], set(), []
    for entry in raw:
        person = _one(entry, known, by_email, errors)
        if person is None:
            continue
        keys = {('contact', person.contact.id)} if person.contact else set()
        if person.email:
            keys.add(('email', person.email.lower()))
        if keys & seen:
            continue
        seen |= keys
        out.append(person)
    if len(out) > policy.MAX_PEOPLE:
        errors.append(words.TOO_MANY.format(limit=policy.MAX_PEOPLE))
    if errors:
        raise ValidationError({'people': list(dict.fromkeys(errors))})
    return out
