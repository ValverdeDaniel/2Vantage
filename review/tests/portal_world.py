"""Shared helpers for the portal's tests (slice 54): a request on a deal with a small synthetic census, and the
anonymous client's own API client. All data is synthetic."""

from rest_framework.test import APIClient

from census.services import add_member
from review import services
from review.models import ClientLink


def person(user, deal, first, last, **values):
    member, _row = add_member(user, deal.id, 'employee', values={'first_name': first, 'last_name': last, **values})
    return member


def make_request(user, deal, asks, *, people=None, security=None, blank=False):
    body = {'asks': asks, 'people': people or [{'name': 'Casey (synthetic)'}], 'blank': blank}
    if security:
        body['security'] = security
    made = services.create(user, deal.id, body)
    link, path, pin = made.links[0]
    return link, path.rsplit('/', 1)[1], pin


def fresh(link):
    return ClientLink.objects.get(pk=link.pk)


def client():
    return APIClient()


def url(token, door=''):
    return f'/api/portal/{token}/{door}'


def verified(api, token, pin):
    """The client proves the PIN; returns the header to send."""
    answer = api.post(url(token, 'verify/'), {'pin': pin}, format='json')
    assert answer.status_code == 200, answer.content
    return {'HTTP_X_LINK_VERIFICATION': answer['X-Link-Verification']}


def page(api, token, **headers):
    return api.get(url(token), **headers)


def save(api, token, answers, door='save/', **headers):
    return api.post(url(token, door), {'answers': answers}, format='json', **headers)


def field(payload, key):
    for section in (payload['intake'] or {}).get('sections', []):
        for entry in section['fields']:
            if entry['key'] == key:
                return entry
    return None


def cell(payload, member_id, column):
    for entry in payload['people']:
        if entry['id'] == member_id:
            for found in entry['fields']:
                if found['column'] == column:
                    return found
    return None
