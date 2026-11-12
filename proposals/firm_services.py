"""The firm's pages, its team and its pictures, written from the Firm pages drawer and the Cover and Pictures cards
(plan.md §6.11, §7.12; J155, OQ41; old Vantage 891f1b3 `FirmPagesPanel.jsx` and the agency team views). Open to
every user, as before. The cover uploads are `cover_services`, which shares this module's Activity helpers.

These rows belong to the firm, not to a deal, so their Activity rows are firm rows: no deal, `subject` "firm_pages",
"team:<id>" or "cover_image:<id>", area `firm`, with before and after of each field a write changed (a person's photo
and an upload's file: their keys only). Every write locks the row it changes, writes nothing when nothing changed and
answers the row. A field's refusal is a 400 naming it; past a cap, a sentence. An Update reverts (`revert`); adding,
removing, a photo and an upload do not (`deals.activity.NOT_REVERTIBLE`, key-only rows). Pictures go through
`documents.images`: checked, re-encoded as JPEG without metadata, stored under a name that says nothing.
"""

import hashlib

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.core.validators import validate_email
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from deals import activity
from documents import images

from .models import FirmPages, TeamMember

AREA = 'firm'
PAGES = 'firm_pages'
PAGE_FIELDS = ('about_text', 'about_stats', 'service_calendar')
PERSON_TEXT = {'name': 120, 'title': 120, 'group': 80, 'phone': 50}
PERSON_FIELDS = (*PERSON_TEXT, 'email', 'bio', 'on_by_default', 'sort_order')
STAT_TEXT = {'value': 24, 'label': 80, 'note': 120}
MEETING_TEXT = {'meeting': 80, 'when': 60}
MAX_TOPICS, TOPIC_TEXT = 12, 120
PHOTO_BYTES, PHOTO_SIDE, PHOTO_STORE = 5 * 1024 * 1024, 6000, 800
NO_PERSON = 'No such person on the team.'
GONE = 'This has been removed since, so this change cannot be reverted.'
WORDS = {
    'about_text': 'Who we are',
    'about_stats': 'The figures',
    'service_calendar': 'The meeting calendar',
    'name': 'The name',
    'title': 'The title',
    'group': "The role on the client's team",
    'phone': 'The phone',
    'email': 'The email',
    'bio': 'The bio',
    'on_by_default': '“On every proposal”',
    'sort_order': 'The order',
}


def words(raw, limit):
    return ' '.join(str(raw or '').split())[:limit]


def _rows(data, key, limit, what):
    value = data.get(key)
    if value in (None, ''):
        return []
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValidationError({key: f'Send the {what} as a list.'})
    if len(value) > limit:
        raise ValidationError({key: f'At most {limit} {what}.'})
    return value


def clean_pages(data):
    """The fields a firm-pages PATCH names, cleaned: About ≤900 (refused past it), ≤6 figures {value, label, note},
    ≤8 meetings {meeting, topics, when}; a row with nothing in it is dropped."""
    if not isinstance(data, dict):
        raise ValidationError({'detail': 'Send {about_text, about_stats, service_calendar}.'})
    out = {}
    if 'about_text' in data:
        text = str(data.get('about_text') or '').strip()
        if len(text) > FirmPages.MAX_ABOUT:
            raise ValidationError({'about_text': f'Who we are can be up to {FirmPages.MAX_ABOUT} characters.'})
        out['about_text'] = text
    if 'about_stats' in data:
        stats = [
            {key: words(row.get(key), limit) for key, limit in STAT_TEXT.items()}
            for row in _rows(data, 'about_stats', FirmPages.MAX_STATS, 'figures')
        ]
        out['about_stats'] = [row for row in stats if row['value'] or row['label']]
    if 'service_calendar' in data:
        meetings = []
        for row in _rows(data, 'service_calendar', FirmPages.MAX_CALENDAR, 'meetings'):
            topics = row.get('topics') or []
            topics = [words(t, TOPIC_TEXT) for t in (topics if isinstance(topics, list) else [topics])]
            found = {key: words(row.get(key), limit) for key, limit in MEETING_TEXT.items()}
            found['topics'] = [t for t in topics if t][:MAX_TOPICS]
            if found['meeting']:
                meetings.append({'meeting': found['meeting'], 'topics': found['topics'], 'when': found['when']})
        out['service_calendar'] = meetings
    return out


def pages_payload(row):
    return {field: getattr(row, field) for field in PAGE_FIELDS}


def record(user, action, summary, subject, diff=None, keys=None):
    changes = [activity.change(subject, diff if diff is not None else keys)]
    return activity.record(None, user, AREA, action, summary, changes=changes, subject=subject)


def save_pages(user, data):
    """PATCH the firm pages → (the pages, Activity row or None when nothing changed)."""
    fields = clean_pages(data)
    with transaction.atomic():
        row = FirmPages.objects.select_for_update().filter(pk=1).first()
        if row is None:
            FirmPages().save()  # the one row, made by the first write (a read never makes it)
            row = FirmPages.objects.select_for_update().get(pk=1)
        diff = {key: [getattr(row, key), value] for key, value in fields.items() if getattr(row, key) != value}
        if not diff:
            return pages_payload(row), None
        for key, (_before, value) in diff.items():
            setattr(row, key, value)
        row.save(update_fields=[*diff, 'updated_at'])
        entry = record(user, 'changed', 'Edited the firm pages', PAGES, diff)
    return pages_payload(row), entry


def person_payload(member):
    """The person as the drawer shows them; `photo_version` changes with each new photo (the photo URL's `?v=`)."""
    version = hashlib.sha1(member.photo.name.encode('utf-8')).hexdigest()[:10] if member.photo else ''
    return {
        'id': member.id,
        **{key: getattr(member, key) for key in PERSON_FIELDS},
        'has_photo': bool(member.photo),
        'photo_version': version,
    }


def clean_person(data, instance=None):
    """The columns a create (a name at least) or an update (those it names) writes; 400 naming each refusal."""
    if not isinstance(data, dict):
        raise ValidationError({'detail': 'Send the person as {name, title, group, phone, email, bio, …}.'})
    errors, out = {}, {}
    for key, limit in PERSON_TEXT.items():
        if key in data or (key == 'name' and instance is None):
            out[key] = words(data.get(key), limit)
    if 'name' in out and not out['name']:
        errors['name'] = 'Give the person a name.'
    if 'email' in data:
        email = str(data.get('email') or '').strip()
        try:
            if email:
                validate_email(email)
            out['email'] = email
        except DjangoValidationError:
            errors['email'] = f'"{email}" is not an email address.'
    if 'bio' in data:
        bio = str(data.get('bio') or '').strip()
        if len(bio) > TeamMember.MAX_BIO:
            errors['bio'] = f'A bio can be up to {TeamMember.MAX_BIO} characters.'
        out['bio'] = bio
    if 'on_by_default' in data:
        if not isinstance(data['on_by_default'], bool):
            errors['on_by_default'] = 'Send true or false.'
        out['on_by_default'] = data['on_by_default'] is True
    if 'sort_order' in data:
        order = data['sort_order']
        if isinstance(order, bool) or not isinstance(order, int) or order < 0:
            errors['sort_order'] = 'Send a whole number, 0 or more.'
        out['sort_order'] = order
    if errors:
        raise ValidationError(errors)
    return out


def _person(member_id):
    found = TeamMember.objects.select_for_update().filter(pk=member_id).first()
    if found is None:
        raise NotFound(NO_PERSON)
    return found


def add_person(user, data):
    fields = clean_person(data)
    with transaction.atomic():
        FirmPages.objects.select_for_update().filter(pk=1).first()  # serializes the cap's count
        if TeamMember.objects.count() >= TeamMember.MAX_MEMBERS:
            raise activity.Refused(f'The team holds at most {TeamMember.MAX_MEMBERS} people. Remove someone first.')
        last = TeamMember.objects.order_by('-sort_order').values_list('sort_order', flat=True).first()
        member = TeamMember.objects.create(**{'sort_order': (last or 0) + 1, **fields})
        diff = {key: [None, getattr(member, key)] for key in PERSON_FIELDS}
        record(user, 'created', 'Added a person to the team', f'team:{member.id}', diff)
    return member


def update_person(user, member_id, data):
    """→ (person, Activity row or None when nothing changed)."""
    with transaction.atomic():
        member = _person(member_id)
        fields = clean_person(data, member)
        diff = {key: [getattr(member, key), value] for key, value in fields.items() if getattr(member, key) != value}
        if not diff:
            return member, None
        for key, (_before, value) in diff.items():
            setattr(member, key, value)
        member.save(update_fields=list(diff))
        entry = record(user, 'changed', 'Edited a person on the team', f'team:{member.id}', diff)
    return member, entry


def drop_file(field):
    """The stored file goes once the write commits (a rolled-back write keeps it)."""
    if field:
        name, storage = field.name, field.storage
        transaction.on_commit(lambda: storage.delete(name))


def remove_person(user, member_id):
    with transaction.atomic():
        member = _person(member_id)
        diff = {key: [getattr(member, key), None] for key in PERSON_FIELDS}
        record(user, 'deleted', 'Removed a person from the team', f'team:{member.id}', diff)
        drop_file(member.photo)
        member.delete()


def set_photo(user, member_id, upload):
    """A person's photo: checked, re-encoded (upright, JPEG, no metadata, long side ≤800), stored as "photo.jpg"."""
    if upload is None:
        raise ValidationError({'photo': 'Choose a PNG or JPEG photo to upload.'})
    try:
        data = images.checked(upload, max_bytes=PHOTO_BYTES, max_side=PHOTO_SIDE, noun='photo')
        stored, _size = images.reencode(data, PHOTO_STORE)
    except images.Refused as refused:
        raise ValidationError({'photo': str(refused)}) from None
    with transaction.atomic():
        member = _person(member_id)
        drop_file(member.photo)
        member.photo.save('photo.jpg', ContentFile(stored), save=False)
        member.save(update_fields=['photo'])
        record(user, 'changed', 'Changed a team photo', f'team:{member.id}', keys=['photo'])
    return member


def remove_photo(user, member_id):
    with transaction.atomic():
        member = _person(member_id)
        if not member.photo:
            return member
        drop_file(member.photo)
        member.photo = ''
        member.save(update_fields=['photo'])
        record(user, 'changed', 'Removed a team photo', f'team:{member.id}', keys=['photo'])
    return member


def revert(entry, user):  # noqa: ARG001 (the reverters' signature)
    """`deals.activity.reverters['firm']`: an Update's earlier values back, refused after a later write."""
    (change,) = entry.changes
    target = change['t']
    later = activity.later_keys(entry)
    if later:
        raise activity.changed_since([WORDS.get(key, key) for _, key in sorted(later)], [k for _, k in sorted(later)])
    if target == PAGES:
        row = FirmPages.objects.select_for_update().filter(pk=1).first()
    else:
        row = TeamMember.objects.select_for_update().filter(pk=int(target.partition(':')[2])).first()
    if row is None:
        raise activity.Refused(GONE)
    diff = {key: [getattr(row, key), before] for key, (before, _) in change['k'].items() if getattr(row, key) != before}
    for key, (_now, value) in diff.items():
        setattr(row, key, value)
    if diff:
        row.save(update_fields=list(diff))
    return [activity.change(target, diff)]
