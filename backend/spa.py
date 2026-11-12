"""The built SPA's page (plan.md §11.2). In the production image every path that is not /api/, /admin/, /accounts/ or
/static/ answers the SPA's index.html, so a deep link or a reload opens its screen on the same origin as the API.
WhiteNoise serves the SPA's assets under /static/. Locally Vite serves the SPA, nothing is built here, and this
answers 404.
"""

from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_safe

from .logs import carries_token


@require_safe
def index(request):
    try:
        page = (settings.SPA_DIR / 'index.html').read_bytes()
    except FileNotFoundError as exc:
        raise Http404('No built SPA here: Vite serves it locally.') from exc
    response = HttpResponse(page, content_type='text/html; charset=utf-8')
    # Asked again on every visit, so a release shows at once; its hashed assets are cached for good (WhiteNoise).
    response['Cache-Control'] = 'no-cache'
    if carries_token(request.path):
        # A client link's page (§3.8, L110): its token never leaves in a Referer, a cache or a search index.
        response['Cache-Control'] = 'private, no-store'
        response['Referrer-Policy'] = 'no-referrer'
        response['X-Robots-Tag'] = 'noindex'
    return response
