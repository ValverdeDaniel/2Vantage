"""Who can hold a share, as the screens read them (plan.md §6.9, §8.18; H11, H12, H95–H98, H101).

- `people()`: the split picker's list in two queries: every Party, then the producer users who have no Party yet
  (computed, never created by a read: their Party is made on the first split save, H95). A person is keyed `p<id>` or
  `u<user id>`; `lookup` maps ('party', id) / ('user', id) to what `rules.validate_rows` checks.
- `roster(viewer_tier)`: the Producers & partners tab: producers (with the login's commission tier badge, H101) and
  partners. The own tier sees the roster only; the producer and house percentages are the all tier's (H97, the old
  "you don't want everybody to know what everybody makes").
"""

from decimal import Decimal

from django.contrib.auth import get_user_model

from accounts.access import commission_tier
from deals import comp as comps

from . import vocab
from .models import Party

HUNDRED = Decimal(100)


def user_name(user):
    return user.get_full_name() or user.username


def _pct(value):
    return None if value is None else format(value.normalize(), 'f')


def _house(value):
    """What the house keeps beside a producer's own share (H97): 100 − it; None for the firm default."""
    return None if value is None else format((HUNDRED - value).normalize(), 'f')


def party_entry(party):
    return {
        'key': f'p{party.id}',
        'id': party.id,
        'user': party.user_id,
        'name': party.name,
        'kind': party.kind,
        'appointed': party.appointed,
        'login': party.user_id is not None,
        'active': party.active,
        'default_split': party.default_split,
        'default_split_label': comps.comp_label(party.default_split),
        'first_year_pct': _pct(party.first_year_pct),
        'renewal_pct': _pct(party.renewal_pct),
    }


def user_entry(user):
    """A producer with a login and no Party yet (H95, H11): listed, never created by a read."""
    return {
        'key': f'u{user.id}',
        'id': None,
        'user': user.id,
        'name': user_name(user),
        'kind': vocab.PRODUCER,
        'appointed': False,
        'login': True,
        'active': True,
        'default_split': None,
        'default_split_label': '',
        'first_year_pct': None,
        'renewal_pct': None,
    }


def _users_without_party():
    return get_user_model().objects.filter(is_active=True, commission_party__isnull=True).order_by('username')


def people():
    """Every party (active or not) and the producer users with no Party: [entry], parties first by name."""
    entries = [party_entry(party) for party in Party.objects.all()]
    entries += [user_entry(user) for user in _users_without_party()]
    return entries


def lookup(entries):
    """{('party', id) | ('user', id): entry} for `rules.validate_rows` and the preview; a login with a Party is found
    by either key."""
    out = {}
    for entry in entries:
        if entry['user']:
            out[('user', entry['user'])] = entry
        if entry['id']:
            out[('party', entry['id'])] = entry
    return out


def key_of(row):
    """The person key of a stored or cleaned row: ('party', id) or ('user', id)."""
    return ('party', row['party']) if row.get('party') else ('user', row.get('user'))


def owner_person(user_id, entries):
    """The owner as a split person: their active producer Party, or their login when they have none yet; None for no
    owner, an inactive Party or an inactive user (H10)."""
    if not user_id:
        return None
    for entry in entries:
        if entry['user'] == user_id and entry['kind'] == vocab.PRODUCER:
            if not entry['active']:
                return None
            return {'party': entry['id']} if entry['id'] else {'user': user_id}
    return None


def picker(entries, rows=()):
    """The editor's list: active people, plus anyone the rows already name (an inactive partner stays readable)."""
    named = {key_of(row) for row in rows}
    return [entry for entry in entries if entry['active'] or (('party', entry['id']) in named)]


def _tier(user):
    user._profile_row = getattr(user, 'profile', None)  # read with select_related: accounts.access asks no query
    return commission_tier(user)


def roster(viewer_tier, *, inactive=False):
    """{producers: [entry + login, tier], partners: [entry + email, phone, npn]} for the Producers & partners tab."""
    full = viewer_tier == 'all'
    parties = Party.objects.select_related('user__profile')
    if not inactive:
        parties = parties.filter(active=True)
    users = _users_without_party().select_related('profile')
    producers, partners = [], []
    for party in parties:
        entry = {**party_entry(party), 'email': party.email, 'phone': party.phone, 'npn': party.npn}
        entry['login_name'] = user_name(party.user) if party.user_id else ''
        entry['tier'] = _tier(party.user) if full and party.user_id else None
        if full:
            entry['first_year_house_pct'] = _house(party.first_year_pct)
            entry['renewal_house_pct'] = _house(party.renewal_pct)
        else:
            entry['first_year_pct'] = entry['renewal_pct'] = None
        (producers if party.kind == vocab.PRODUCER else partners).append(entry)
    for user in users:
        entry = {**user_entry(user), 'email': user.email, 'phone': '', 'npn': ''}
        entry['login_name'] = user_name(user)
        entry['tier'] = _tier(user) if full else None
        producers.append(entry)
    return {'producers': producers, 'partners': partners, 'full': full}
