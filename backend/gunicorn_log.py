"""gunicorn's access log without link tokens (plan.md §11.2; L110). start.sh runs gunicorn with
`--logger-class backend.gunicorn_log.TokenSafeLogger`. A request on a token path is not logged, and neither is one
whose Referer is a token page (a portal page's own asset and API requests would otherwise carry its token there).
"""

from urllib.parse import urlsplit

from gunicorn.glogging import Logger

from backend.logs import carries_token


def quiet(environ):
    """True when the request's path, or the page it came from, carries a link token."""
    referer = urlsplit(str(environ.get('HTTP_REFERER') or '')).path
    return any(carries_token(path) for path in (environ.get('PATH_INFO'), environ.get('RAW_URI'), referer))


class TokenSafeLogger(Logger):
    def access(self, resp, req, environ, request_time):
        if quiet(environ):
            return
        super().access(resp, req, environ, request_time)
