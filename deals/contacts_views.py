"""The client's contacts over HTTP (plan.md §7.3; B13, M30). Thin: parse → service or selector → respond."""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import contacts, selectors, services
from .models import Client, Contact
from .views import MAX_ID


def _fields(data):
    return {key: data[key] for key in contacts.FIELDS if key in data}


class ClientContactsView(APIView):
    """GET clients/{id}/contacts/ → {contacts, primary_id} · POST {role?, name, title, email, phone, is_primary} →
    201 contact (an HR admin when no role is sent; M30). A bad email or role answers 400."""

    def get(self, request, pk):
        if pk > MAX_ID:
            raise Http404
        return Response(selectors.client_contacts(get_object_or_404(Client, pk=pk)))

    def post(self, request, pk):
        if pk > MAX_ID:
            raise Http404
        get_object_or_404(Client, pk=pk)
        contact = services.create_contact(request.user, pk, **_fields(request.data))
        return Response(selectors.contact_row(contact), status=status.HTTP_201_CREATED)


class ContactView(APIView):
    """PATCH contacts/{id}/ (any of the fields) → contact · DELETE → 204."""

    def _known(self, pk):
        if pk > MAX_ID or not Contact.objects.filter(pk=pk).exists():
            raise Http404
        return pk

    def patch(self, request, pk):
        contact, _changed = services.update_contact(request.user, self._known(pk), **_fields(request.data))
        return Response(selectors.contact_row(contact))

    def delete(self, request, pk):
        services.delete_contact(request.user, self._known(pk))
        return Response(status=status.HTTP_204_NO_CONTENT)
