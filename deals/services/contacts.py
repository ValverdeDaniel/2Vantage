"""The client's contacts (plan.md §4.6, §6.2, §7.3; B13, M30, OQ106): add, edit and remove, one primary per client.

Contacts are client-level, so they outlive a deal. Each write locks the Client row first (it serializes the one
primary and the order), then the contact. Marking one primary clears the others; a prior broker is never primary
(`deals.contacts.primary`, B32). A contact's details name a person, so Activity keeps the keys alone (§3.8): the rows
say what changed, never the words, and Revert refuses them with its key-only sentence.
"""

import re

from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from .. import activity, contacts
from ..models import Client, Contact
from ..values import locked

AREA = 'contacts'
EMAIL = re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')  # intake's email_format check (B8)
TEXT = ('name', 'title', 'email', 'phone')


def clean(data, *, partial):
    """The fields sent, cleaned: a known role, texts trimmed to their limits, a well-formed email, is_primary a bool.
    Raises ValidationError keyed by field."""
    out, errors = {}, {}
    if 'role' in data or not partial:
        role = data.get('role') or contacts.HR_ADMIN  # the first edit creates an HR admin (M30)
        if role not in contacts.LABELS:
            errors['role'] = [f'A contact is one of: {", ".join(contacts.LABELS.values())}.']
        out['role'] = role
    for key in TEXT:
        if key in data:
            text = ' '.join(str(data[key] if data[key] is not None else '').split())
            if len(text) > contacts.LIMITS[key]:
                errors[key] = [f'Keep this under {contacts.LIMITS[key]} characters.']
            out[key] = text
    if out.get('email') and not EMAIL.fullmatch(out['email']):
        errors['email'] = [f'"{out["email"]}" is not a valid email address.']
    if 'is_primary' in data:
        out['is_primary'] = data['is_primary'] is True or str(data['is_primary']).lower() in ('true', '1')
    if errors:
        raise ValidationError(errors)
    return out


def _refuse_broker_primary(role, is_primary):
    if is_primary and role not in contacts.CLIENT_SIDE:
        raise ValidationError({'is_primary': ["A prior broker can't be the client's main contact."]})


def _clear_primary(client, keep_id=None):
    Contact.objects.filter(client=client, is_primary=True).exclude(pk=keep_id).update(is_primary=False)


def _record(user, client, action, summary, contact, keys):
    deal = client.deals.order_by('-id').first()
    change = activity.change(f'contact:{contact.id}', sorted(keys))
    subject = '' if deal else f'client:{client.id}'
    return activity.record(deal, user, AREA, action, summary, changes=[change], keys_only=True, subject=subject)


@transaction.atomic
def create_contact(user, client_id, **data):
    """A new contact (an HR admin unless a role is given). Raises Client.DoesNotExist and ValidationError."""
    client = locked(Client, client_id)
    fields = clean(data, partial=False)
    _refuse_broker_primary(fields['role'], fields.get('is_primary'))
    if fields.get('is_primary'):
        _clear_primary(client)
    last = Contact.objects.filter(client=client).aggregate(last=Max('sort_order'))['last']
    contact = Contact.objects.create(client=client, sort_order=0 if last is None else last + 1, **fields)
    _record(user, client, 'created', f'Added a contact ({contacts.label(contact.role)})', contact, fields)
    return contact


def _locked_contact(contact_id):
    client_id = Contact.objects.values_list('client_id', flat=True).get(pk=contact_id)
    client = locked(Client, client_id)  # lock order: the client, then its contact
    return client, Contact.objects.select_for_update().get(pk=contact_id)


@transaction.atomic
def update_contact(user, contact_id, **data):
    """Edit any of the fields. Returns (contact, [changed keys]); an unchanged contact writes nothing. Raises
    Contact.DoesNotExist and ValidationError."""
    client, contact = _locked_contact(contact_id)
    fields = clean(data, partial=True)
    changed = [key for key, value in fields.items() if getattr(contact, key) != value]
    if not changed:
        return contact, []
    _refuse_broker_primary(fields.get('role', contact.role), fields.get('is_primary', contact.is_primary))
    if fields.get('is_primary') and 'is_primary' in changed:
        _clear_primary(client, keep_id=contact.id)
    for key in changed:
        setattr(contact, key, fields[key])
    contact.save(update_fields=changed)
    _record(user, client, 'updated', 'Edited a contact', contact, changed)
    return contact, changed


@transaction.atomic
def delete_contact(user, contact_id):
    """Removes the contact for good (B13 asks first). Raises Contact.DoesNotExist."""
    client, contact = _locked_contact(contact_id)
    role, contact_ref = contact.role, Contact(id=contact.id)
    contact.delete()
    _record(user, client, 'deleted', f'Removed a contact ({contacts.label(role)})', contact_ref, ['contact'])
