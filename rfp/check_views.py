"""The export check's doors (plan.md §7.11; K52, K69–K72). Read only: they write nothing.

- `GET deals/{id}/rfp/checks/` → `{checks_stamp, cards: {key: {status ready|problems|unsigned, count}}, deal:
  [problem]}`: the packet grid's pills, one call; the page asks again only when `checks_stamp` moves (K52).
- `GET deals/{id}/rfp/check/?file=<key>` → `{key, label, ok, problems, ack}` for any key of the one key space,
  `packet` or `draft-<key>`: what the modal shows before a download (K69); 400 for a key the deal does not have.
No query parameter is named `format` (K.6).
"""

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .cards import packet
from .check import report
from .check.stamp import stamp
from .context import Request
from .views import _deal


def unknown(key):
    return ValidationError({'file': [f'“{key}” is not one of this RFP’s files.']})


class ChecksView(APIView):
    def get(self, request, pk):
        ctx = Request(_deal(pk))
        return Response({'checks_stamp': stamp(ctx), **report.pills(ctx)})


class CheckView(APIView):
    def get(self, request, pk):
        ctx = Request(_deal(pk))
        key = str(request.query_params.get('file') or '')[:80]
        try:
            return Response(report.report(ctx, key, packet.rows(ctx)))
        except report.Unknown:
            raise unknown(key) from None
