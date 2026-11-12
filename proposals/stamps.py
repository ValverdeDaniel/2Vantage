"""The builder payload's `stamps {files, firm}` (plan.md §8.14; J.6.5; F3, J107): what the Export viewer keys its
previews on, so a preview is built again only when something a client file prints may have changed.

- `files` moves with the deal's latest recorded write (rule 4: every write is in Activity), and at midnight (the files
  print today's date). A completed mark moves nothing (J107: "marks ignored"), nor do downloads and views, which
  change no file. A superset of "something a client file prints changed": any recorded write to the deal moves it.
- `firm` moves with the agency settings (logo, colour, contact, producer), the firm pages and the team, which Django
  admin edits without an Activity row.
Reads only: a fixed number of queries whatever the deal holds (Q.3 #4).
"""

import hashlib

from deals import clock
from deals.activity import ACCESS
from deals.models import Activity, AgencySettings

from .models import FirmPages, TeamMember
from .services import AREA, MARKED

AGENCY_FIELDS = ('name', 'address', 'city_state_zip', 'phone', 'email', 'brand_color', 'logo', 'producer_name')
TEAM_FIELDS = ('id', 'name', 'title', 'group', 'phone', 'email', 'bio', 'photo', 'on_by_default', 'sort_order')


def _digest(*parts):
    return hashlib.sha1(repr(parts).encode('utf-8')).hexdigest()[:16]


def files(deal):
    latest = (
        Activity.objects.filter(deal_id=deal.id)
        .exclude(action__in=ACCESS)
        .exclude(area=AREA, action=MARKED)
        .order_by('-updated_at', '-id')
        .values_list('id', 'count', 'updated_at')
        .first()
    )
    return _digest(clock.today().isoformat(), latest)


def firm():
    agency = AgencySettings.objects.filter(pk=1).values_list(*AGENCY_FIELDS).first()
    pages = FirmPages.objects.values_list('about_text', 'about_stats', 'service_calendar', 'updated_at').first()
    team = list(TeamMember.objects.order_by('id').values_list(*TEAM_FIELDS))
    return _digest(agency, pages, team)


def stamps(deal):
    return {'files': files(deal), 'firm': firm()}
