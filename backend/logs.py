"""Link tokens stay out of the logs (plan.md §11.2, §3.5; L110). The client portal's paths carry a link's token in the
URL, so in production request logs and error reports drop every record about them: settings.py puts
`DropTokenPaths` on the console handler, and start.sh gives gunicorn `backend.gunicorn_log.TokenSafeLogger`.
Pure: no Django import, so gunicorn can load it before the app.
"""

import logging
import re

# /api/portal/<token>/ (the portal's API), /portal/<token> (its page) and /b/<token> (old links, "This link has moved").
TOKEN_PATHS = ('/api/portal/', '/portal/', '/b/')
_NAMED = re.compile(r'(?:^|[\s"\'=(])(?:' + '|'.join(re.escape(path) for path in TOKEN_PATHS) + ')')


def carries_token(path):
    """True when a request path is one of the token paths."""
    return str(path or '').startswith(TOKEN_PATHS)


def names_token_path(text):
    """True when a log line names a token path (Django's "Not Found: /api/portal/…", a traceback's request line)."""
    return bool(_NAMED.search(str(text or '')))


class DropTokenPaths(logging.Filter):
    """Drops a record about a token path: by the request Django attaches, or by the path its message names."""

    def filter(self, record):
        request = getattr(record, 'request', None)
        if carries_token(getattr(request, 'path', '')):
            return False
        try:
            message = record.getMessage()
        except (TypeError, ValueError):  # a malformed record still logs, as logging itself would try to
            message = str(record.msg)
        return not names_token_path(message)
