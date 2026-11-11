"""The one place code reads the date (plan.md §12.1). Tests patch this module.

`today()` is the agency's date, not UTC's: after 7 or 8 pm Eastern, UTC is already tomorrow (§3.5).
"""

from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


def now():
    return timezone.now()


def agency_zone():
    return ZoneInfo(settings.AGENCY_TIME_ZONE)


def today():
    return now().astimezone(agency_zone()).date()


def local(dt):
    return dt.astimezone(agency_zone()) if dt else None
