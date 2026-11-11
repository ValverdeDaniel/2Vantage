import uuid

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from deals.downloads import safe_filename
from deals.models import Deal


def upload_to(instance, filename):
    return f'deals/{instance.deal_id}/{uuid.uuid4().hex}-{safe_filename(filename)}'


class Document(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to=upload_to, max_length=400)
    original_name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    kind = models.CharField(max_length=20, default='other')
    role = models.CharField(max_length=12, blank=True)
    carrier = models.CharField(max_length=200, blank=True)
    lines = models.JSONField(default=list, blank=True)
    label = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=10, default='staff')
    review_state = models.CharField(max_length=10, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['deal', 'uploaded_at'])]
        ordering = ['-uploaded_at', '-id']

    def __str__(self):
        return self.label or self.original_name


@receiver(post_delete, sender=Document)
def _delete_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
