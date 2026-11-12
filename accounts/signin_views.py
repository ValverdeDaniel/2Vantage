"""Sign-in's ways in (plan.md §7.2, §8.2; slice 47): which are open, and Microsoft 365 sign-in's two browser steps.

- `GET auth/options/` (public) → `{password, microsoft: {start, messages} | null}`: what the sign-in page draws.
  `messages` holds the refusals' sentences by code; the callback names a code in `/login?signin=<code>`.
- `GET auth/microsoft/?next=/deals/12` (public) → 302 to the provider's authorize page (404 while Microsoft 365
  sign-in is off). It keeps the pending sign-in in the session.
- `GET auth/microsoft/callback/?code=&state=` (public; the provider sends the browser here) → the firm account's
  session and 302 to `next`, or 302 to `/login?signin=<code>`.
These two GETs write the session, as every sign-in does; nothing else (no Activity, no user row: rule 9).
"""

from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import firm, oidc

START = '/api/auth/microsoft/'
LOGIN_PAGE = '/login'


def _safe_next(raw):
    """A path on this site to land on after signing in, else home: never another site, never a server page."""
    path = str(raw or '')[:500]
    if not path.startswith('/') or path.startswith('//') or '\\' in path or path.startswith(('/api/', '/login')):
        return '/'
    return path


def _redirect(url):
    response = HttpResponseRedirect(url)
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'no-referrer'
    return response


def _refused(code):
    return _redirect(f'{LOGIN_PAGE}?signin={code}')


class SignInOptionsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        microsoft = {'start': START, 'messages': firm.REFUSALS} if settings.AUTH_OIDC else None
        return Response({'password': settings.AUTH_PASSWORD_SIGNIN, 'microsoft': microsoft})


class MicrosoftStartView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'login'

    def get(self, request):
        if not settings.AUTH_OIDC:
            raise Http404('Microsoft 365 sign-in is not set up.')
        try:
            return _redirect(oidc.begin(request.session, _safe_next(request.query_params.get('next'))))
        except oidc.Refused as refused:
            return _refused(refused.code)


class MicrosoftCallbackView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'login'

    def get(self, request):
        if not settings.AUTH_OIDC:
            raise Http404('Microsoft 365 sign-in is not set up.')
        try:
            email, next_path = oidc.finish(request.session, request.query_params)
        except oidc.Refused as refused:
            return _refused(refused.code)
        refusal = firm.sign_in(request, email)
        return _refused(refusal) if refusal else _redirect(_safe_next(next_path))
