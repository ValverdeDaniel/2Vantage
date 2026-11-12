"""The firm's pages and team (plan.md §7.12 `proposal/firm-pages/`, `proposal/team/`; J155, OQ41): what the Firm
pages drawer reads and writes, open to every user. Writes go through `firm_services`; a photo is served to the
drawer only (a client file embeds its pixels) and never kept by the browser.
"""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import firm_services as firm
from .models import FirmPages, TeamMember
from .story import firm_read


class FirmPagesView(APIView):
    def get(self, request):
        """{about_text, about_stats, service_calendar}: blank until written; a read never makes the row."""
        return Response(firm.pages_payload(FirmPages.get()))

    def patch(self, request):
        found, entry = firm.save_pages(request.user, request.data)
        return Response({**found, 'activity_id': entry.id if entry else None})


class TeamView(APIView):
    def get(self, request):
        """[person]: {id, name, title, group, phone, email, bio, on_by_default, sort_order, has_photo}, in order."""
        return Response([firm.person_payload(member) for member in TeamMember.objects.all()])

    def post(self, request):
        member = firm.add_person(request.user, request.data)
        return Response(firm.person_payload(member), status=status.HTTP_201_CREATED)


class PersonView(APIView):
    def patch(self, request, member_id):
        member, entry = firm.update_person(request.user, member_id, request.data)
        return Response({**firm.person_payload(member), 'activity_id': entry.id if entry else None})

    def delete(self, request, member_id):
        firm.remove_person(request.user, member_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PhotoView(APIView):
    def get(self, request, member_id):
        """The stored photo (a re-encoded JPEG), or 404 when the person has none."""
        member = get_object_or_404(TeamMember, pk=member_id)
        data = firm_read.file_bytes(member.photo)
        if not data:
            return Response({'detail': 'No photo.'}, status=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(data, content_type='image/jpeg')
        response['Cache-Control'] = 'private, no-store'
        return response

    def post(self, request, member_id):
        """multipart `photo` → the person, with its photo."""
        return Response(firm.person_payload(firm.set_photo(request.user, member_id, request.FILES.get('photo'))))

    def delete(self, request, member_id):
        return Response(firm.person_payload(firm.remove_photo(request.user, member_id)))
