"""The firm's cover images and the Pictures card's thumbnails (plan.md §7.12 `proposal/covers/`,
`proposal/cover-images/`; J32, J33, J35; old Vantage 891f1b3 `views/covers.py`, `ProposalCoverPreviewView`). Every
user may upload or delete, as before; a client file never sees a path or an id: it embeds the pixels.
"""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import cover_services as covers
from . import cover_tiles, pictures
from .models import CoverImage
from .story import firm_read

THUMB_CACHE = 'private, max-age=86400'  # an upload's thumbnail never changes under its id


def cover_payload(image):
    return {
        'id': image.id,
        'key': f'upload:{image.id}',
        'label': image.label,
        'width': image.width,
        'height': image.height,
    }


def _jpeg(data, cache):
    response = HttpResponse(data, content_type='image/jpeg')
    response['Cache-Control'] = cache
    return response


class CoverTilesView(APIView):
    def get(self, request):
        """?picture= (a stock key, `none`, or absent for the default) → the tile PDF, with an ETag (304: unchanged)."""
        asked = request.query_params.get('picture') or ''
        tag = cover_tiles.etag(asked)
        if request.headers.get('If-None-Match') == tag:
            response = HttpResponse(status=304)
        else:
            data, _labels = cover_tiles.tiles_pdf(asked)
            response = HttpResponse(data, content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="cover-designs.pdf"'
        response['ETag'] = tag
        response['Cache-Control'] = 'private, no-cache'
        return response


class CoverImagesView(APIView):
    def get(self, request):
        """[{id, key, label, width, height}] in the tiles' order."""
        return Response([cover_payload(image) for image in CoverImage.objects.order_by('created_at', 'id')])

    def post(self, request):
        """multipart `image` (+ `label`) → the upload; 400 for a refused file, 409 past 24."""
        image = covers.upload_cover(request.user, request.FILES.get('image'), request.data.get('label') or '')
        return Response(cover_payload(image), status=status.HTTP_201_CREATED)


class CoverImageView(APIView):
    def delete(self, request, image_id):
        covers.delete_cover(request.user, image_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CoverThumbView(APIView):
    def get(self, request, image_id):
        image = get_object_or_404(CoverImage, pk=image_id)
        data = firm_read.file_bytes(image.thumb)
        if not data:
            return Response({'detail': 'No such cover image.'}, status=status.HTTP_404_NOT_FOUND)
        return _jpeg(data, THUMB_CACHE)


class StockThumbView(APIView):
    def get(self, request, key):
        data = pictures.stock_thumbnail(key)
        if not data:
            return Response({'detail': 'No such picture.'}, status=status.HTTP_404_NOT_FOUND)
        return _jpeg(data, THUMB_CACHE)
