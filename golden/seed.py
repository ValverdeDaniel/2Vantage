"""Builds the golden deals from their specs, through the services, never raw SQL (plan.md §12.6).

Idempotent: building a deal first removes every client of its name, so re-running replaces it.
"""

from collections import namedtuple

from django.contrib.auth import get_user_model
from django.db import transaction

from deals.lifecycle import NEW_CLIENT, PROSPECT
from deals.models import Client
from deals.services import create_client, delete_client, set_status
from proposals import services as proposals
from quotes import services as plans

from . import files, specs

Golden = namedtuple('Golden', 'deal refs spec')  # refs: {spec ref: plan id}

SEED_USERNAME = 'golden-seed'


def seed_user():
    """The first active superuser, else a `golden-seed` user who cannot sign in."""
    User = get_user_model()
    user = User.objects.filter(is_superuser=True, is_active=True).order_by('id').first()
    if user:
        return user
    user, created = User.objects.get_or_create(username=SEED_USERNAME, defaults={'first_name': 'Golden seed'})
    if created:
        user.set_unusable_password()
        user.save()
    return user


@transaction.atomic
def remove(spec, user):
    """Delete every client named as the spec's client, with its deals (the client service)."""
    for client_id in Client.objects.filter(name=spec['client']).values_list('id', flat=True):
        delete_client(user, client_id)


def _plan(user, deal, plan, refs, printed=None):
    """Create one plan. `printed` (files.Attached) names the synthetic file that prints some of its values: a
    workbook's values carry their file and cell; a PDF's values, typed after the rest, carry their file (slice 15)."""
    if plan.get('copy_of'):  # the negotiated option is made the way a member would: Duplicate and name it, then rates
        copy = plans.copy_plan(user, refs[plan['copy_of']], plan['name'])
        plans.update_plan(user, copy.id, {'values': plan['values']})
        return copy.id
    links = [refs[ref] for ref in plan['links']]
    from_file = {key: plan['values'][key] for key in (printed.keys if printed else []) if key in plan['values']}
    with_cells = bool(printed and printed.cells)
    created = plans.create_plan(
        user,
        deal,
        line=plan['line'],
        role=plan['role'],
        carrier=plan['carrier'],
        name=plan['name'],
        values=plan['values'] if with_cells else {k: v for k, v in plan['values'].items() if k not in from_file},
        renews_id=links[0] if plan['role'] == 'renewal' else None,
        replaces_ids=links if plan['role'] == 'alternate' else [],
        document=printed.document if with_cells else None,
        cells=printed.cells if with_cells else None,
    )
    if from_file and not with_cells:
        plans.update_plan(user, created.id, {'values': from_file}, document=printed.document)
    return created.id


@transaction.atomic
def build(spec, user):
    """Create one golden deal from its spec, replacing any earlier one. Returns Golden(deal, refs, spec)."""
    remove(spec, user)
    status = spec.get('status', PROSPECT)  # GD1 and GD2 are Prospects (§5.1, slice 6)
    _, deal = create_client(
        user,
        name=spec['client'],
        relationship=PROSPECT if status == NEW_CLIENT else status,
        effective_date=spec['effective_date'],
        requested_lines=spec['lines'],
    )
    if status == NEW_CLIENT:  # a New client is made only by a sale or Convert to client (CL6)
        set_status(user, deal.client_id, NEW_CLIENT)
    printed = files.attach(user, deal, spec)
    refs = {}
    for plan in spec['plans']:
        refs[plan['ref']] = _plan(user, deal, plan, refs, printed.get(plan['ref']))
    typed = [
        {'id': refs[plan['ref']], 'enrollment': plan['enrollment'], 'on': True}
        for plan in spec['plans']
        if plan.get('enrollment')
    ]
    plans.set_enrollment(user, deal, typed)
    plans.star(user, deal, [refs[ref] for ref in spec['starred']], True)
    for ref in spec['recommended']:
        plans.set_recommended(user, refs[ref], True)
    for package in spec['packages']:
        plans.create_package(user, deal, package['line'], package['name'], [refs[ref] for ref in package['plans']])
    proposals.save_config(user, deal, {'reasons': spec['reasons']})
    deal.refresh_from_db()
    return Golden(deal, refs, spec)


def build_all(user=None, only=None):
    """{key: Golden} for every spec (or the keys in `only`), in key order."""
    user = user or seed_user()
    return {key: build(specs.load(key), user) for key in specs.keys() if not only or key in only}


def remove_all(user):
    for spec in specs.load_all():
        remove(spec, user)
