"""The PHI gate's access-log check (plan.md §11.4 item 4, §3.8, §12.9; Q.9 row 47 on GD6; slice 47).

Every download or view of a file that carries member data writes one `downloaded` or `viewed` row — a view may count
on the file's row of the last ten minutes instead — with the document id when the file is a stored document, and
never its name or a person's; the rows never move "Last updated". The doors are found the way a person finds them, in
the app's own payloads on a fresh GD6 at Ready to market (its census arrived): every Documents file of a PHI kind or
that the member-data screen found people in, the census's export, template and import view, every RFP file flagged
PHI with its sheet view, the packet and each email draft, the questionnaire's PDF and preview, and the quote board
exported with lasers. A file without member data (the RFP cover) writes nothing. Lives in the composition root
because it crosses every app that serves a file.
"""

from dataclasses import dataclass
from urllib.parse import quote

import pytest

from deals.activity import ACCESS
from deals.models import Activity
from quotes import services as quotes

pytestmark = pytest.mark.django_db


@dataclass
class Door:
    url: str
    action: str  # 'downloaded', 'viewed', or None for a file without member data
    document: dict | None = None  # the stored file it serves (the Documents payload), if any


def document_doors(api, deal):
    phi_kinds = {kind['key'] for kind in api.get('/api/meta/').json()['document_kinds'] if kind['phi']}
    files = [doc for doc in api.get(f'/api/deals/{deal.id}/documents/').json() if doc['kind'] in phi_kinds or
             doc['screen']['lists_members']]  # fmt: skip
    for doc in files:
        yield Door(f'/api/documents/{doc["id"]}/download/', 'downloaded', doc)
        yield Door(f'/api/documents/{doc["id"]}/download/?inline=1', 'viewed', doc)
        if doc['shape'] == 'sheet':
            yield Door(f'/api/documents/{doc["id"]}/sheet/', 'viewed', doc)


def census_doors(api, deal, by_id):
    yield Door(f'/api/deals/{deal.id}/census/export/', 'downloaded')
    yield Door(f'/api/deals/{deal.id}/census/template/', 'downloaded')  # prefilled from the roster
    for imp in api.get(f'/api/deals/{deal.id}/census/').json()['imports']:
        yield Door(f'/api/census/imports/{imp["id"]}/', 'viewed', by_id[imp['document_id']])


def rfp_doors(api, deal, by_id):
    page = api.get(f'/api/deals/{deal.id}/rfp/').json()
    rows = {row['key']: row for row in page['packet']['rows']}
    for key, row in rows.items():
        if not row['available']:
            continue
        stored = by_id.get(int(key[4:])) if key.startswith('doc-') else None
        yield Door(f'/api/deals/{deal.id}/rfp/files/{key}/', 'downloaded' if row['phi'] else None, stored)
        if row['section'] == 'census':
            yield Door(f'/api/deals/{deal.id}/rfp/files/{key}/look/', 'viewed')
    carries = any(row['include'] and row['phi'] for row in rows.values())
    yield Door(f'/api/deals/{deal.id}/rfp/files/packet/', 'downloaded' if carries else None)
    for draft in page['drafts']['rows']:
        attached = any(rows[key]['phi'] for key in draft['attachment_keys'] if key in rows)
        yield Door(f'/api/deals/{deal.id}/rfp/files/draft-{draft["key"]}/', 'downloaded' if attached else None)


def questionnaire_doors(api, deal):
    for form in api.get(f'/api/deals/{deal.id}/questionnaires/').json()['forms']:
        yield Door(f'/api/deals/{deal.id}/questionnaires/{form["key"]}/pdf/', 'downloaded')
        yield Door(f'/api/deals/{deal.id}/questionnaires/{form["key"]}/pdf/?inline=1', 'viewed')


def laser_door(user, deal):
    plan = quotes.create_plan(user, deal, line='stop_loss', role='current', carrier='Sun Life', name='Spec')
    quotes.update_plan(user, plan.id, {'sl_lasers': 'Claimant 4471: $250,000 (synthetic)'})
    query = f'line=stop_loss&plans={plan.id}&columns=sl_lasers'
    return Door(f'/api/deals/{deal.id}/plans/board-export/?{query}', 'downloaded')


def rows_of(deal):
    return {row['id']: row for row in Activity.objects.filter(deal=deal).values()}


def last_updated(api, deal):
    found = api.get(f'/api/clients/?q={quote(deal.client.name)}').json()['results']
    return next(row['last_activity_at'] for row in found if row['deal']['id'] == deal.id)


def people(api, deal):
    """Every roster name on the deal: none may reach an access row or a download name."""
    page = api.get(f'/api/deals/{deal.id}/census/', {'page_size': 500}).json()
    return {str(member['values'].get(key) or '') for member in page['members'] for key in ('first_name', 'last_name')}


def _read(answer):
    if getattr(answer, 'streaming', False):
        return b''.join(answer.streaming_content)
    return answer.content


def problems(api, deal, door, names):
    before = rows_of(deal)
    answer = api.get(door.url)
    _read(answer)
    if answer.status_code != 200:
        return [f'{door.url}: answered {answer.status_code}']
    after = rows_of(deal)
    touched = [after[pk] for pk in after if before.get(pk) != after[pk]]
    if door.action is None:
        return [f'{door.url}: a file without member data wrote {len(touched)} row(s)'] if touched else []
    if len(touched) != 1 or touched[0]['action'] != door.action:
        return [f'{door.url}: wrote {[row["action"] for row in touched]}, not one {door.action} row']
    row, found = touched[0], []
    if door.document and row['document_id'] != door.document['id']:
        found.append(f'{door.url}: the row names document {row["document_id"]}, not {door.document["id"]}')
    told = f'{row["summary"]} {answer.get("Content-Disposition", "")}'
    stem = door.document['original_name'].rsplit('.', 1)[0] if door.document else None
    if stem and stem in told:
        found.append(f'{door.url}: the file name reached "{told}"')
    found += [f'{door.url}: a person ("{name}") reached "{told}"' for name in names if name and name in told]
    return found


def test_PHI4_every_download_or_view_of_a_phi_file_writes_its_access_row(api, user, get_to_market):
    deal = get_to_market.ready().built.deal
    picked = api.patch(f'/api/deals/{deal.id}/rfp/', {'carriers': {'add': ['aetna', 'cigna']}}, format='json')
    assert picked.status_code == 200  # carriers asked, so the email drafts exist
    door = laser_door(user, deal)
    stamp, names = last_updated(api, deal), people(api, deal)
    stored = list(document_doors(api, deal))
    by_id = {each.document['id']: each.document for each in stored}
    doors = [*stored, *census_doors(api, deal, by_id), *rfp_doors(api, deal, by_id), *questionnaire_doors(api, deal)]
    doors.append(door)
    kinds = {each.url.split('/')[4 if each.url.startswith('/api/deals/') else 2] for each in doors}
    assert {'documents', 'census', 'rfp', 'questionnaires', 'plans'} <= kinds  # every family of door was found
    assert any(each.url.endswith('/files/packet/') for each in doors) and any('/draft-' in each.url for each in doors)
    assert any(each.action is None for each in doors)  # and a file with no member data, which writes nothing
    found = [problem for each in doors for problem in problems(api, deal, each, names)]
    assert not found, '\n'.join(found)
    assert last_updated(api, deal) == stamp
    assert set(Activity.objects.filter(deal=deal, action__in=ACCESS).values_list('actor', flat=True)) == {user.id}
