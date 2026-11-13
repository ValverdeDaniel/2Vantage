"""Rows a test sets up through the owners' own services (review's request and send), then dated back: synthetic."""

from datetime import timedelta

from deals import clock
from review import services as review_services
from review.models import ClientLink

CENSUS_FILE = {'census': {'file': True}}


def sent_ask(user, deal, asks=None, days_ago=4, name='Casey (synthetic)'):
    """A request for the census file, sent `days_ago` days ago to one person: the link."""
    made = review_services.create(user, deal.id, {'asks': asks or CENSUS_FILE, 'people': [{'name': name}]})
    link = made.links[0][0]
    review_services.mark_sent(user, link.id, copied=True)
    ClientLink.objects.filter(pk=link.id).update(sent_at=clock.now() - timedelta(days=days_ago))
    return link
