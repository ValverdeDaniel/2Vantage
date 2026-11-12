"""PHI canaries through the questionnaire's files (Q.8; G23, G63, §3.8): a medical answer and a claimant's identifier
print on the carrier's form, and reach no Activity row, no file name or label, no header and no check text."""

import json

import pytest

from deals.models import Activity
from documents.models import Document
from questionnaire import services
from questionnaire.models import Questionnaire

from .pdfs import fields, texts
from .world import make_world

pytestmark = pytest.mark.django_db
FL, SIIA = 'fl_blue_51', 'stop_loss_siia'
MEDICAL, CLAIMANT = 'CANARY-MED-7731 dialysis', 'Canary Claimant'


def test_Q8_medical_answers_print_and_go_nowhere_else(user, api):
    deal = make_world(user, lines=('medical', 'stop_loss'))
    services.choose_form(user, deal.id, 'stop_loss_disclosure', SIIA)
    services.set_answers(user, deal.id, FL, {'chkMedCon': 'Yes', 'txtMcComments': MEDICAL})
    services.set_answers(user, deal.id, SIIA, {'no_risks': 'No'})
    risk = Questionnaire.objects.get(deal=deal, form=SIIA).rows['risks'][0]['id']
    services.set_answers(user, deal.id, SIIA, {f'risks.{risk}.risk_identifier': CLAIMANT})
    seen = []
    for form in (FL, SIIA):
        base = f'/api/deals/{deal.id}/questionnaires/{form}/'
        seen.append(json.dumps(api.get(base + 'check/').json()))
        answer = api.get(base + 'pdf/')
        seen.append(answer['Content-Disposition'])
        data = b''.join(answer.streaming_content)
        seen.append(texts(data) + json.dumps(fields(data), default=str))
        services.sign(user, deal.id, form, 'officer', 'Pat Sample', authorized=True, sign_anyway=True)
    printed = seen[2] + seen[5]
    assert 'CANARY-MED-7731' in printed and CLAIMANT in printed  # the carrier's form carries them, as it must
    # (the disclosure's claimant sits in its AcroForm field, the medical comment in Florida Blue's comments box)
    elsewhere = [seen[0], seen[1], seen[3], seen[4]]
    elsewhere += [f'{a.summary} {json.dumps(a.changes)}' for a in Activity.objects.filter(deal=deal)]
    elsewhere += [f'{d.original_name} {d.label}' for d in Document.all_objects.filter(deal=deal)]
    assert not any('CANARY' in text or CLAIMANT in text for text in elsewhere)
