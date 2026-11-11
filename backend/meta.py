"""GET /api/meta/ — every vocabulary the frontend needs (plan.md §7.1). The frontend never hard-codes these."""

from rest_framework.response import Response
from rest_framework.views import APIView

from deals import lines, stages
from documents import kinds
from quotes import fields


def _pairs(choices):
    return [{'key': key, 'label': label} for key, label in choices]


class MetaView(APIView):
    def get(self, request):
        return Response(
            {
                'lines': lines.meta(),
                'tiers': [{'code': code, 'label': label} for code, label in lines.TIERS],
                'stages': _pairs(stages.STAGES),
                'relationships': [{'key': 'new', 'label': 'New'}, {'key': 'existing', 'label': 'Existing'}],
                'funding': _pairs(lines.FUNDING),
                'document_kinds': _pairs(kinds.KINDS),
                'document_roles': _pairs(kinds.ROLES),
                'plans': fields.meta(),
            }
        )
