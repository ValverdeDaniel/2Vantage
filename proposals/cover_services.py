"""The firm's cover images (plan.md §6.11, §7.12 `proposal/cover-images/`; J33; old Vantage 891f1b3 `views/covers.py`,
`branding.prepare_cover`): an upload for every proposal, picked per deal as the cover's picture or any dark page's.
Firm rows like the firm's pages (`firm_services`): no deal, `subject` "cover_image:<id>", area `firm`, the file's key
only. Neither an upload nor a delete is reverted; a deleted upload's files go once the delete commits, and a proposal
that wore it falls back (`pictures`).
"""

from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from deals import activity
from documents import images

from . import firm_services as firm
from .models import CoverImage, FirmPages

NO_COVER = 'No such cover image.'


def upload_cover(user, upload, label=''):
    """A cover image for every proposal (J33): ≤24 firm-wide, checked, re-encoded (≤2,400 px) with a ≤600 px
    thumbnail, stored as "cover.jpg" and "cover-thumb.jpg"."""
    if upload is None:
        raise ValidationError({'image': 'Choose a PNG or JPEG image to upload.'})
    try:
        data = images.checked(upload, max_bytes=CoverImage.MAX_BYTES, max_side=CoverImage.MAX_SIDE, noun='cover image')
        stored, (width, height) = images.reencode(data, CoverImage.STORE_SIDE)
        thumb = images.thumbnail(stored, CoverImage.THUMB_SIDE)
    except images.Refused as refused:
        raise ValidationError({'image': str(refused)}) from None
    with transaction.atomic():
        FirmPages.objects.select_for_update().filter(pk=1).first()  # serializes the cap's count
        if CoverImage.objects.count() >= CoverImage.MAX_IMAGES:
            raise activity.Refused(
                f'The firm already has {CoverImage.MAX_IMAGES} cover images. Delete one before adding another.'
            )
        image = CoverImage(label=firm.words(label, CoverImage.MAX_LABEL), width=width, height=height, uploaded_by=user)
        image.image.save('cover.jpg', ContentFile(stored), save=False)
        image.thumb.save('cover-thumb.jpg', ContentFile(thumb), save=False)
        image.save()
        firm.record(user, 'created', 'Uploaded a cover image', f'cover_image:{image.id}', keys=['image'])
    return image


def delete_cover(user, image_id):
    """Delete an upload for everyone: proposals that wear it fall back (`pictures`), its files go on commit."""
    with transaction.atomic():
        image = CoverImage.objects.select_for_update().filter(pk=image_id).first()
        if image is None:
            raise NotFound(NO_COVER)
        firm.record(user, 'deleted', 'Deleted a cover image', f'cover_image:{image.id}', keys=['image'])
        firm.drop_file(image.image)
        firm.drop_file(image.thumb)
        image.delete()
