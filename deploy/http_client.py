"""A small HTTP client for the release gate and the smoke check (deploy/README.md): the standard library only, no
redirects followed, cookies kept by hand. Cloud Run's front end adds X-Forwarded-Proto; the local rehearsal, which
speaks plain HTTP inside Docker, sends it itself (`forwarded_proto='https'`), as Cloud Run would.
"""

import json
import secrets
import urllib.error
import urllib.request
from http.cookies import SimpleCookie
from urllib.parse import urlsplit


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Response:
    def __init__(self, status, headers, body):
        self.status, self.headers, self.body = status, headers, body

    def header(self, name):
        return self.headers.get(name) or ''

    def json(self):
        return json.loads(self.body.decode('utf-8'))

    def text(self):
        return self.body.decode('utf-8', errors='replace')


class Client:
    def __init__(self, base_url, forwarded_proto=None, timeout=30):
        self.base = base_url.rstrip('/')
        self.forwarded_proto = forwarded_proto
        self.timeout = timeout
        self.cookies = {}
        self._opener = urllib.request.build_opener(_NoRedirect)
        scheme = forwarded_proto or urlsplit(self.base).scheme
        self.origin = f'{scheme}://{urlsplit(self.base).netloc}'

    def request(self, method, path, body=None, headers=None, content_type=None):
        sent = {'Accept': 'application/json, text/html;q=0.9, */*;q=0.8'}
        if self.forwarded_proto:
            sent['X-Forwarded-Proto'] = self.forwarded_proto
        if self.cookies:
            sent['Cookie'] = '; '.join(f'{name}={value}' for name, value in self.cookies.items())
        if method not in ('GET', 'HEAD'):
            # Django's CSRF check: the token from the cookie, and an Origin and Referer on this site (§3.6).
            sent.update({'X-CSRFToken': self.cookies.get('csrftoken', ''), 'Origin': self.origin})
            sent['Referer'] = f'{self.origin}/'
        if content_type:
            sent['Content-Type'] = content_type
        sent.update(headers or {})
        request = urllib.request.Request(self.base + path, data=body, headers=sent, method=method)
        try:
            with self._opener.open(request, timeout=self.timeout) as answer:
                response = Response(answer.status, answer.headers, answer.read())
        except urllib.error.HTTPError as error:
            response = Response(error.code, error.headers, error.read())
        for line in response.headers.get_all('Set-Cookie') or []:
            for name, morsel in SimpleCookie(line).items():
                self.cookies[name] = morsel.value
        return response

    def get(self, path, **kwargs):
        return self.request('GET', path, **kwargs)

    def post_json(self, path, data):
        return self.request('POST', path, json.dumps(data).encode(), content_type='application/json')

    def post_file(self, path, fields, filename, content, file_type='application/octet-stream'):
        boundary = f'----2vantage{secrets.token_hex(12)}'
        parts = []
        for name, value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f'Content-Type: {file_type}\r\n\r\n'.encode()
            + content
            + b'\r\n'
        )
        parts.append(f'--{boundary}--\r\n'.encode())
        return self.request('POST', path, b''.join(parts), content_type=f'multipart/form-data; boundary={boundary}')


class Checks:
    """Prints one line per check and remembers the failures."""

    def __init__(self):
        self.failed = []

    def check(self, name, ok, detail=''):
        print(f'{"PASS" if ok else "FAIL"}  {name}{f"  ({detail})" if detail else ""}', flush=True)
        if not ok:
            self.failed.append(name)
        return ok

    def done(self, what):
        if self.failed:
            print(f'{what}: {len(self.failed)} failed: {", ".join(self.failed)}')
            return 1
        print(f'{what}: every check passed.')
        return 0
