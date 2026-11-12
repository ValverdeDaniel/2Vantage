"""The private Cloud Storage bucket that holds staging's and production's files (plan.md §11.2, §3.8).

settings.py names `PrivateBucket` as the default storage only when GS_BUCKET_NAME is set, and Django imports a storage
backend on first use, so a local run never loads this module or Google's libraries. All code reaches files through
Django's storage API (`deals/<id>/<uuid>-<name>`), so the bucket and the local MEDIA_ROOT are interchangeable.
"""

from urllib.parse import urljoin

from django.conf import settings
from django.utils.encoding import filepath_to_uri
from storages.backends.gcloud import GoogleCloudStorage


class PrivateBucket(GoogleCloudStorage):
    """Never hands out a link to an object, public or signed: files stream through the app's authenticated download
    endpoints, which record every PHI download (§3.6, §3.8). Like the filesystem storage under MEDIA_URL, `url()`
    names a path nothing serves, so Django admin's file widgets (the agency logo) still render."""

    def url(self, name, parameters=None):
        return urljoin(settings.MEDIA_URL, filepath_to_uri(name))
