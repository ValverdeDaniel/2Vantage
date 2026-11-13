"""The walk of the staging canary scan (slice 47; plan.md §11.4 item 5, §12.9; Q.8; deploy/phi-gate.md).

A person's census work, scripted with this run's canary census (deploy/canaries.py) on a new synthetic client: upload
the census file, map and apply it, open and search the roster, edit a person (and three edits the app refuses), answer
on the client portal as the employer (deploy/canary_portal.py: the PIN, a census answer, a refused SSN, an added
person, a census file, Submit; slice 54), view
and download every file that carries the people (Documents, the census export and template, the RFP's carrier files,
packet and drafts), type a stop-loss laser and export the board with it, then archive the client. On the way it
checks the answers that must never carry PHI: error bodies, download names, redirects, the deal's header and its feed.
It saves the canaries (--out) for the log query that follows (deploy/canary_scan.py). Standard library only.

    CANARY_PASSWORD=… python deploy/canary_walk.py --url https://<web host> --user <staff username> --out c.json
    CANARY_SESSION=<the sessionid cookie of a Microsoft 365 sign-in> python deploy/canary_walk.py --url … --out …
    # the dev stack, inside the backend container (deploy/canary_scan.sh runs this, then the log query):
    CANARY_PASSWORD=golden-admin-pw python deploy/canary_walk.py --url http://localhost:8000 --user golden-admin
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canaries as made  # noqa: E402
from canary_portal import portal, questionnaire  # noqa: E402
from http_client import Checks, Client  # noqa: E402

CARRIERS = ['aetna', 'cigna']  # asked, so the RFP has email drafts


class Walk:
    def __init__(self, client, canaries):
        self.client, self.checks, self.canaries = client, Checks(), canaries
        self.values = canaries['values']
        self.strings = sorted({form for forms in made.searched(canaries).values() for form in forms})

    def call(self, what, method, path, body=None, expect=(200,), clean=False):
        """One request, checked for its status; with `clean`, its body and headers must carry no canary."""
        if method == 'GET':
            answer = self.client.get(path)
        elif body is None:
            answer = self.client.request(method, path)
        else:
            answer = self.client.request(method, path, json.dumps(body).encode(), content_type='application/json')
        self.checks.check(what, answer.status in expect, f'answered {answer.status}')
        if clean:
            self.clean(what, answer.text())
        headers = ' '.join(answer.header(name) for name in ('Content-Disposition', 'Location'))
        self.clean(f'{what}: its headers', headers)
        return answer

    def clean(self, what, text):
        found = [string for string in self.strings if string in text.lower()]
        if found:
            self.checks.check(f'{what} carries no canary', False, f'found "{found[0]}"')


def sign_in(walk, user):
    session = os.environ.get('CANARY_SESSION', '')
    if session:
        walk.client.cookies['sessionid'] = session
    walk.client.get('/api/auth/csrf/')
    if not session:
        password = os.environ.get('CANARY_PASSWORD') or os.environ.get('SMOKE_PASSWORD', '')
        walk.call(f'{user} signs in', 'POST', '/api/auth/login/', {'username': user, 'password': password})
    return walk.call('the session is a staff session', 'GET', '/api/auth/me/').status == 200


def census(walk):
    made_client = walk.call('a synthetic client', 'POST', '/api/clients/', {
        'name': f'Canary walk {walk.canaries["run"]} (synthetic)'}, expect=(201,))  # fmt: skip
    if made_client.status != 201:
        return None
    deal = made_client.json()['deal']['id']
    client_id = made_client.json()['client']['id']
    sent = walk.client.post_file(f'/api/deals/{deal}/documents/', {'kind': 'census', 'lines': '[]'},
                                 made.file_name(walk.canaries), made.census_csv(walk.canaries), 'text/csv')  # fmt: skip
    walk.checks.check('the canary census uploads', sent.status == 201, f'answered {sent.status}')
    if sent.status != 201:
        return deal, client_id, None
    document = sent.json()['id']
    started = walk.call('its import is proposed', 'POST', f'/api/deals/{deal}/census/imports/', {
        'document_id': document}, expect=(201,))  # fmt: skip
    if started.status == 201:
        imp = started.json()['id']
        walk.call('the mapping opens', 'GET', f'/api/census/imports/{imp}/')
        walk.call('the import applies', 'POST', f'/api/census/imports/{imp}/apply/', {}, expect=(200,), clean=False)
    return deal, client_id, document


def roster(walk, deal):
    page = walk.call('the roster opens', 'GET', f'/api/deals/{deal}/census/')
    # The roster's name search, as the census page sends it (frontend/src/api/census.js): posted, never in a URL.
    found = walk.call('the roster is searched by name', 'POST', f'/api/deals/{deal}/census/search/', {
        'q': walk.values['last_name']})  # fmt: skip
    hits = found.json().get('members', []) if found.status == 200 else []
    walk.checks.check('the search finds the canary family', bool(hits), f'{len(hits)} people')
    members = page.json().get('members', []) if page.status == 200 else []
    if not members:
        walk.checks.check('the roster lists the canary people', False, 'nobody on the roster')
        return
    url = f'/api/census/members/{members[0]["id"]}/'
    walk.call('a person is edited', 'PATCH', url, {'values': {'city': walk.values['edited_city']}})
    refused = [
        ({'values': {'ssn': '***-**-0000'}}, (400,)),
        ({'values': {'city': walk.values['city']}, 'expect': {'city': walk.values['address']}}, (409, 200)),
        ({'values': {walk.values['last_name']: walk.values['first_name']}}, (400,)),
    ]
    for body, expect in refused:
        walk.call('a refused edit names no value', 'PATCH', url, body, expect=expect, clean=True)


def files(walk, deal, document):
    if document:
        walk.call('the census file downloads', 'GET', f'/api/documents/{document}/download/')
        walk.call('the census file is viewed', 'GET', f'/api/documents/{document}/download/?inline=1')
        walk.call('its sheet is viewed', 'GET', f'/api/documents/{document}/sheet/')
    walk.call('the census export downloads', 'GET', f'/api/deals/{deal}/census/export/')
    walk.call('the census template downloads', 'GET', f'/api/deals/{deal}/census/template/')
    walk.call('carriers are asked', 'PATCH', f'/api/deals/{deal}/rfp/', {'carriers': {'add': CARRIERS}})
    page = walk.call('the RFP opens', 'GET', f'/api/deals/{deal}/rfp/')
    if page.status != 200:
        return
    rfp = page.json()
    for row in rfp['packet']['rows']:
        if row['available'] and row['phi']:
            walk.call(f'the RFP file {row["key"]} downloads', 'GET', f'/api/deals/{deal}/rfp/files/{row["key"]}/')
    walk.call('the RFP packet downloads', 'GET', f'/api/deals/{deal}/rfp/files/packet/', expect=(200, 400))
    for draft in rfp['drafts']['rows']:
        walk.call(f'the {draft["key"]} draft downloads', 'GET', f'/api/deals/{deal}/rfp/files/draft-{draft["key"]}/')


def lasers(walk, deal):
    plan = walk.call(
        'a stop-loss plan',
        'POST',
        f'/api/deals/{deal}/plans/',
        {'line': 'stop_loss', 'role': 'current', 'carrier': 'Sun Life', 'name': 'Spec (synthetic)'},
        expect=(201,),
    )
    if plan.status != 201:
        return
    plan_id = plan.json()['id']
    walk.call('lasers are typed', 'PATCH', f'/api/plans/{plan_id}/', {'values': {'sl_lasers': walk.values['laser']}})
    query = f'line=stop_loss&plans={plan_id}&columns=sl_lasers'
    walk.call('the board exports with lasers', 'GET', f'/api/deals/{deal}/plans/board-export/?{query}')


def surfaces(walk, deal, client_id):
    walk.call("the deal's header names nobody", 'GET', f'/api/deals/{deal}/', clean=True)
    walk.call("the deal's feed names nobody", 'GET', f'/api/deals/{deal}/activity/', clean=True)
    walk.call('the client is archived', 'POST', f'/api/clients/{client_id}/archive/', {'archived': True})


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--url', required=True)
    parser.add_argument('--user', default='', help='a staff username (password: CANARY_PASSWORD), or CANARY_SESSION')
    parser.add_argument('--out', default='canaries.json', help="where this run's canaries go, for canary_scan.py")
    parser.add_argument('--forwarded-proto', help='send X-Forwarded-Proto, as Cloud Run does (local rehearsal)')
    args = parser.parse_args()
    canaries = made.make()
    made.save(canaries, args.out)
    print(f'Canary run {canaries["run"]}, started {canaries["started_at"]}; canaries in {args.out}', flush=True)
    walk = Walk(Client(args.url, args.forwarded_proto), canaries)
    if sign_in(walk, args.user):
        made_deal = census(walk)
        if made_deal:
            deal, client_id, document = made_deal
            roster(walk, deal)
            portal(walk, deal, made)  # the client portal's leg (slice 54): deploy/canary_portal.py
            questionnaire(walk, deal)  # a medical answer on the questionnaire (slice 58): deploy/canary_portal.py
            files(walk, deal, document)
            lasers(walk, deal)
            surfaces(walk, deal, client_id)
    if not os.environ.get('CANARY_SESSION'):  # a borrowed browser session stays signed in
        walk.client.request('POST', '/api/auth/logout/')
    return walk.checks.done('Canary walk')


if __name__ == '__main__':
    sys.exit(main())
