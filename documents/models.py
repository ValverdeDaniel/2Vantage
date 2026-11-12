"""The Document row (plan.md §6.3, E.6). `upload` (services) is the only door that makes one from a person's file.

`objects` hides archived files, so every list (the checklist, the packet, the coverage chips, the portal slots) drops a
removed file without a filter of its own; `all_objects` serves value links, opening a file and "Show removed files"
(E15, O.3.7). A row's bytes go only after its deletion commits, whether a purge or a deal's or client's cascade
removed it (E96), so a rolled-back delete never loses a file.
"""

import logging
import uuid

from django.conf import settings
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from deals.downloads import safe_filename
from deals.models import Deal

logger = logging.getLogger(__name__)


def upload_to(instance, filename):
    return f'deals/{instance.deal_id}/{uuid.uuid4().hex}-{safe_filename(filename)}'


class ActiveDocuments(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(archived_at__isnull=True)


class Document(models.Model):
    SOURCES = [('staff', 'Staff'), ('client', 'Client')]
    REVIEW_STATES = [('', 'Not reviewed'), ('accepted', 'Accepted'), ('wrong', 'Wrong')]

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to=upload_to, max_length=400)
    original_name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)  # PDFs only, read at upload (E7)
    page_labels = models.JSONField(default=dict, blank=True)  # printed page labels {"3": "2"}, from the quote reader
    kind = models.CharField(max_length=20)  # documents/kinds.py; required (E6)
    role = models.CharField(max_length=12, blank=True)
    carrier = models.CharField(max_length=200, blank=True)
    lines = models.JSONField(default=list, blank=True)
    label = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=10, choices=SOURCES, default='staff')
    review_state = models.CharField(max_length=10, choices=REVIEW_STATES, blank=True)
    # The client link and ask slot a portal upload answered; a plain integer, because review sits to the right.
    link_id = models.PositiveBigIntegerField(null=True, blank=True)
    slot = models.CharField(max_length=60, blank=True)
    # The member-data screen run at upload (D52): {version, left_out_pages, image_pages, lists_members}.
    screen = models.JSONField(default=dict, blank=True)
    # Set by Issue and by signing: archive and purge refuse a protected file (O.3.7).
    protected = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    all_objects = models.Manager()
    objects = ActiveDocuments()

    class Meta:
        default_manager_name = 'objects'  # related lists (deal.documents) hide archived files too
        indexes = [models.Index(fields=['deal', 'uploaded_at'])]
        ordering = ['-uploaded_at', '-id']

    def __str__(self):
        return self.label or self.original_name


def remove_bytes(storage, name):
    """Delete stored bytes; never raises (the row is already gone, and a failure here must not break the request)."""
    if not name:
        return
    try:
        storage.delete(name)
    except Exception:  # noqa: BLE001 - a stray file is found later by sweep_orphan_files (E98)
        logger.warning('Could not remove the bytes of a deleted document.')


@receiver(post_delete, sender=Document)
def _delete_file_on_commit(sender, instance, **kwargs):
    """E96: a deleted row's bytes go once the deletion commits; a rolled-back delete keeps them."""
    if instance.file:
        storage, name = instance.file.storage, instance.file.name
        transaction.on_commit(lambda: remove_bytes(storage, name))
