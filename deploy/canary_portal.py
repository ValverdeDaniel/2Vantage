"""The client portal's leg of the canary walk (slice 54; plan.md §12.9 "the portal flow", §11.4 item 5, §7.14;
deploy/phi-gate.md item 5). Standard library only.

On the walk's own synthetic deal, after its census is applied: staff make a request that asks the whole census and
the census file (so it needs the PIN, OQ80); then a second client with no session, as the employer's browser, opens
the link (428), proves the PIN, reads the page, answers a person's phone with this run's canary, tries an SSN (refused,
and the refusal must name no value), adds a person under the canary names, uploads a census file whose name carries
them, and submits. The page itself shows the people (that is what it is for); every other answer, the refusals and
the headers must carry no canary, and the log query that follows must find none of the portal's traffic either.
"""

import json
import secrets

from http_client import Client

ASKS = {'census': {'scope': 'all', 'file': True}}


def _token(path):
    return path.rsplit('/', 1)[1]


def _multipart(fields, filename, content, file_type):
    boundary = f'----2vantage{secrets.token_hex(12)}'
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()
    ]
    head = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"'
    head += f'\r\nContent-Type: {file_type}'
    parts.append(f'{head}\r\n\r\n'.encode() + content + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts), f'multipart/form-data; boundary={boundary}'


def _cell(page, first_name, column):
    for person in page.get('people', []):
        if person['title'].startswith(first_name):
            for field in person['fields']:
                if field['column'] == column:
                    return person['id'], field['base']
    return None, ''


def portal(walk, deal, made):
    """`walk`: the canary walk (its signed-in client, checks and canaries); `made`: deploy/canaries.py."""
    values = walk.values
    asked = walk.call('a request for the census on a link', 'POST', f'/api/deals/{deal}/review/requests/', {
        'people': [{'name': 'Canary walk contact (synthetic)'}], 'asks': ASKS}, expect=(201,), clean=True)  # fmt: skip
    if asked.status != 201:
        return
    link = asked.json()['links'][0]
    token, pin = _token(link['path']), link['pin']
    employer = Client(walk.client.base, walk.client.forwarded_proto)
    base = f'/api/portal/{token}/'

    def call(what, method, door, body=None, proof=None, expect=(200,), clean=True, raw=None):
        headers = {'X-Link-Verification': proof} if proof else {}
        if raw:
            answer = employer.request(method, base + door, raw[0], headers=headers, content_type=raw[1])
        elif body is not None:
            answer = employer.request(method, base + door, json.dumps(body).encode(), headers, 'application/json')
        else:
            answer = employer.request(method, base + door, headers=headers)
        walk.checks.check(what, answer.status in expect, f'answered {answer.status}')
        if clean:
            walk.clean(what, answer.text())
        walk.clean(f'{what}: its headers', ' '.join(answer.header(n) for n in ('Content-Disposition', 'Location')))
        return answer

    call('the link asks for the PIN first', 'GET', '', expect=(428,))
    proved = call('the PIN opens it', 'POST', 'verify/', {'pin': pin})
    proof = proved.header('X-Link-Verification')
    page = call('the page opens with the people', 'GET', '', proof=proof, clean=False)
    if page.status != 200:
        return
    member, base_ = _cell(page.json(), values['first_name'], 'phone')
    if member:
        answer = {f'census:{member}:phone': {'value': values['phone'], 'base': base_}}
        call('a census answer is saved', 'POST', 'save/', {'answers': answer}, proof)
        refused = {f'census:{member}:ssn': {'value': values['ssn'], 'base': ''}}
        call('an SSN is refused, naming no value', 'POST', 'save/', {'answers': refused}, proof, expect=(400,))
    else:
        walk.checks.check('the canary person is on the page', False, 'not found')
    person = {'kind': 'employee', 'first_name': values['spouse_first_name'], 'last_name': values['last_name']}
    call('a person is added', 'POST', 'people/', {'people': [person]}, proof, expect=(201,), clean=False)
    body = _multipart(
        {'slot': 'census_file'}, made.file_name(walk.canaries), made.census_csv(walk.canaries), 'text/csv'
    )
    call('the census file is uploaded', 'POST', 'files/', proof=proof, expect=(201,), clean=False, raw=body)
    call('the answers are submitted', 'POST', 'submit/', {'answers': {}}, proof)
    call('the census template is blank', 'GET', 'census-template/', proof=proof)
    walk.call('the Board names nobody from the census', 'GET', f'/api/deals/{deal}/review/board/', clean=True)
