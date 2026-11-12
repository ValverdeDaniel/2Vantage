"""GET /api/meta/ — every vocabulary the frontend needs (plan.md §7.1). The frontend never hard-codes these."""

from rest_framework.response import Response
from rest_framework.views import APIView

from deals import carriers, lifecycle, lines, stages
from documents import kinds
from quotes import board_presets, fields


def _pairs(choices):
    return [{'key': key, 'label': label} for key, label in choices]


class MetaView(APIView):
    def get(self, request):
        return Response(
            {
                'lines': lines.meta(),
                'tiers': [{'code': code, 'label': label} for code, label in lines.TIERS],
                'stages': _pairs(stages.STAGES),
                'relationships': lifecycle.meta(),
                'funding': _pairs(lines.FUNDING),
                **kinds.meta(),  # document_kinds (with their flags), document_buckets, document_roles
                'plans': fields.meta(),
                'carriers': carriers.meta(),
                'board': board_presets.meta(),  # the Advisor's columns, sorts, sliders and budget rungs (F31)
            }
        )
