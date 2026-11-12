"""Saved parts of a proposal, Mine and Shared (plan.md §7.12 `proposal/templates/`; J68, OQ7): the TEMPLATE bars of
How the documents look (`layout`), the rows card (`rows`) and the Executive summary (`summary`). Writes go through
`template_services`; applying one is the builder's PATCH of the deal.
"""

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals import lines

from . import template_services as templates
from . import template_store as store
from .models import ProposalTemplate


class TemplatesView(APIView):
    def get(self, request):
        """?kind= (required) &line= → [template]: the built-in ones first, then this person's and the shared ones."""
        kind = request.query_params.get('kind') or ''
        line = request.query_params.get('line') or ''
        if kind not in dict(ProposalTemplate.KINDS):
            raise ValidationError({'kind': [f'Give a kind: {", ".join(dict(ProposalTemplate.KINDS))}.']})
        if line and line not in lines.BY_KEY:
            raise ValidationError({'line': [f'"{line}" is not a line of coverage.']})
        saved = [store.payload(row, request.user) for row in store.visible(request.user, kind, line)]
        return Response([*store.built_in(kind), *saved])

    def post(self, request):
        row = templates.create(request.user, request.data)
        return Response(store.payload(row, request.user), status=status.HTTP_201_CREATED)


class TemplateView(APIView):
    def patch(self, request, template_id):
        row, _entry = templates.update(request.user, template_id, request.data)
        return Response(store.payload(row, request.user))

    def delete(self, request, template_id):
        templates.delete(request.user, template_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
