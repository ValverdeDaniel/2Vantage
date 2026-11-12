"""GD6's road to Ready to market after its seed (plan.md §13.4, Q.4; slice 40), each step through the services a
person's clicks call.

The seed builds GD6 with its intake answered (slice 39) and nothing else of the gate: no contact, no BOR, no census,
the coverage unconfirmed, nothing ticked — so it reads Blocked. Each step below is one gap closed, and `ready` runs
them all, after which GD6 reads Ready to market (checkpoint "ready"):
- `contacts`: the spec's contacts (an HR admin with a name and an email: Contacts OK, B13);
- `census`: the 60-person census (`census`, `arrives: "ready"`), uploaded and imported as a member who clicks Apply;
  its tiers equal the current plan's typed counts, so the Advisor's figures do not move (Census OK, B33);
- `intent`: each line the spec names answered in force and shopped, then the coverage confirmed (B20);
- `bor`: the BOR signed with the spec's signer (B29);
- `ticks`: the checklist items a person ticks — COBRA, and "On file" for the questionnaire, renewal and invoice (B27).
Each returns the Golden. Tests reach these through the root conftest only.
"""

from django.core.files.uploadedfile import SimpleUploadedFile

from census import services as census
from deals.services import create_contact
from documents import services as documents
from intake import services as intake

from . import census_files, census_roster


def contacts(user, built):
    for contact in built.spec['get_to_market']['contacts']:
        create_contact(user, built.deal.client_id, **contact)
    return built


def census_arrives(user, built):
    deal, _refs, spec = built
    data = census_files.client_xlsx(census_roster.people(spec))
    upload = SimpleUploadedFile(spec['census']['file'], data)
    document = documents.upload(user, deal, upload, {'kind': 'census'})
    census.apply_import(user, census.create_import(user, deal.id, document.id).id)
    return built


def intent(user, built):
    for line in built.spec['get_to_market']['in_force']:
        intake.set_intent(user, built.deal.id, line=line, has_today=True, this_year='market')
    intake.confirm_intent(user, built.deal.id)
    return built


def bor(user, built):
    intake.sign_bor(user, built.deal.id, built.spec['get_to_market']['bor_signer'])
    return built


def ticks(user, built):
    for item in built.spec['get_to_market']['ticks']:
        intake.set_checklist_item(user, built.deal.id, item, checked=True)
    return built


def ready(user, built):
    for step in (contacts, census_arrives, intent, bor, ticks):
        built = step(user, built)
    return built
