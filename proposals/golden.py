"""Builds the golden deals through the services, never raw SQL (plan.md §12.6)."""

from django.contrib.auth import get_user_model
from django.db import transaction

from deals.models import Client
from deals.services import create_client
from quotes import marks
from quotes import services as plans

from . import golden_data, services

# The negotiated Cigna option is made the way a member would: Copy as alternate, then new rates.
COPIES = {'CG1N': 'CG1'}


def seed_user():
    User = get_user_model()
    user = User.objects.filter(is_superuser=True, is_active=True).order_by('id').first()
    if user:
        return user
    user, created = User.objects.get_or_create(username='golden-seed', defaults={'first_name': 'Golden seed'})
    if created:
        user.set_unusable_password()
        user.save()
    return user


@transaction.atomic
def build(spec, user):
    """Create one golden deal from its spec. Returns (deal, {ref: plan id})."""
    Client.objects.filter(name=spec['client']).delete()
    _, deal = create_client(
        user, name=spec['client'], effective_date=spec['effective_date'], requested_lines=spec['lines']
    )
    refs = {}
    for ref, line, role, carrier, name, links, rates, _, extra in spec['plans']:
        values = {**extra, **rates}
        if ref in COPIES:
            copy = plans.copy_as_alternate(user, refs[COPIES[ref]])
            plans.update_plan(user, copy.id, {'name': name, 'values': values})
            refs[ref] = copy.id
            continue
        link_ids = [refs[r] for r in links]
        plan = plans.create_plan(
            user,
            deal,
            line=line,
            role=role,
            carrier=carrier,
            name=name,
            values=values,
            renews_id=link_ids[0] if role == 'renewal' else None,
            replaces_ids=link_ids if role == 'alternate' else [],
        )
        refs[ref] = plan.id
    typed = [
        {'id': refs[ref], 'enrollment': enrollment, 'on': True}
        for ref, *_, enrollment, _extra in spec['plans']
        if enrollment
    ]
    marks.set_enrollment(user, deal, typed)
    marks.star(user, deal, [refs[r] for r in spec['starred']], True)
    for ref in spec['recommended']:
        marks.set_recommended(user, refs[ref], True)
    for line, name, members in spec['packages']:
        marks.create_package(user, deal, line, name, [refs[r] for r in members])
    services.save_config(user, deal, {'reasons': spec['reasons']})
    return deal, refs


def build_all(user=None):
    user = user or seed_user()
    return [build(spec, user) for spec in golden_data.DEALS]
