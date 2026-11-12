"""A synthetic filled Florida Blue 51+ form and its score, for reader trials (plan.md §10.4, §12.8; G109; slice 52). Dev
only: `manage.py questionnaire_sample` uses it; the app never does, and no test reads a real form.

`SAMPLE` is a filled form as the questionnaire stores it (house formats: ISO dates, the options as listed), every name
and number invented. `printed_sample()` stamps it onto the bundled blank through the questionnaire's own exporter, so
the file Claude reads is the carrier's form with typed answers. `score(key, read)` compares a staged read
(`StagedRead.read`) with the key in counts only, never a value: answers right, wrong, missed and extra, and the rows
of each section read exactly or not.
"""

from . import forms, slots, values
from .engine import walk
from .pdf.build import render
from .pdf.printed import Printed

FORM = 'fl_blue_51'
CLIENT = 'Example Trial Fabrication (synthetic)'

SCALARS = {
    'txtCoName': 'Example Trial Fabrication LLC',
    'dteAnnivDate': '2027-01-01',
    'txtBusAdd': '400 Sample Parkway',
    'City': 'Orlando',
    'State': 'FL',
    'ZipCode': '32801',
    'drpSIC': '3441',
    'TextField2': '00-1234567',
    'numTAP': '74',
    'numCurrentCarrierEligCount': '69',
    'chkFBPrior': 'No',
    'drpNumCarr': '2',
    'txtRsnBid': 'Renewal Increase',
    'chkVirgin': 'Yes',
    'txtCurrentCarrier': 'Example Health Plan',
    'drpEEContMethod': 'Percentage',
    'numERConPercent': '80',
    'numDepConPercent': '50',
    'chkMedCon': 'Yes',
    'txtMcComments': 'Synthetic note: one member counted in two rows.',
    'txtgrprepname': 'Riley Example',
    'txtTitleOfficer': 'Chief Financial Officer',
    'txtagentname': 'Dana Sample / 0000000',
    'txtAgencyName': 'Example Benefits Agency',
}
ROWS = {
    'plans': [
        {'txtCurrPlanName': 'Example Health PPO 2000', 'dteCurrCarrEffDt': '2026-01-01', 'numCurrRatePrem': '41250',
         'numRenPrem': '45900'},
        {'txtCurrPlanName': 'Example Health HMO 1500', 'dteCurrCarrEffDt': '2026-01-01', 'numCurrRatePrem': '22180',
         'numRenPrem': '24870'},
    ],
    'conditions': [
        {'drpMedCat': 'Kidney', 'drpMedCondition': 'Renal Failure', 'drpMedConDetail': 'Chronic',
         'numNumEEMedCon': '1'},
        {'drpMedCat': 'Cancer', 'drpMedCondition': 'Breast Cancer', 'numNumEEMedCon': '2', 'numCancerDetailyes': '1',
         'num_CancerDetailsno': '1', 'txtMedIll': 'Synthetic: in treatment since spring.'},
        {'drpMedCat': 'Cardiovascular/Heart', 'drpMedCondition': 'Atrial Fibrillation &/or Flutter',
         'numNumEEMedCon': '1'},
    ],
}  # fmt: skip


def sample():
    """(scalars, rows) of the filled form, with the SIC description its code pairs with."""
    sic = dict(forms.FORMS[FORM]['tables']['sic_codes'])
    return {**SCALARS, 'drpSICDesc': sic[SCALARS['drpSIC']]}, {block: list(listed) for block, listed in ROWS.items()}


def printed_sample():
    """The filled form's bytes: the sample stamped onto the bundled blank (DRAFT: nobody signed it)."""
    form = forms.FORMS[FORM]
    scalars, rows = sample()
    answers = dict(scalars)
    stored_rows = {}
    for block, listed in rows.items():
        stored_rows[block] = [{'id': n} for n in range(1, len(listed) + 1)]
        for number, row in enumerate(listed, start=1):
            answers.update({slots.key(block, number, key): value for key, value in row.items()})
    stored = values.Stored(answers, {}, {}, [], stored_rows)
    shown_scalars, by_block = walk.visible_values(form, values.shown(form, stored, {}))
    numbered = {block: [(n, vals) for n, (_id, vals) in enumerate(listed, 1)] for block, listed in by_block.items()}
    return render(Printed(form, shown_scalars, numbered, None, None, CLIENT))


def key():
    """The answer key as JSON-ready data."""
    scalars, rows = sample()
    return {'form': FORM, 'answers': scalars, 'rows': rows}


def _same(left, right):
    return str(left or '').strip().lower() == str(right or '').strip().lower()


def score(key_data, read):
    """{answers: {key, right, wrong, missed, extra}, rows: {block: {key, read, exact, values_right, values}}}."""
    found = {name: entry['value'] for name, entry in (read.get('answers') or {}).items()}
    wanted = key_data['answers']
    out = {
        'answers': {
            'key': len(wanted),
            'right': sum(1 for name, value in wanted.items() if name in found and _same(found[name], value)),
            'wrong': sum(1 for name, value in wanted.items() if name in found and not _same(found[name], value)),
            'missed': sum(1 for name in wanted if name not in found),
            'extra': sum(1 for name in found if name not in wanted),
        },
        'rows': {},
    }
    for block, listed in key_data['rows'].items():
        got = [row['values'] for row in (read.get('rows') or {}).get(block) or []]
        pairs = list(zip(listed, got, strict=False))
        out['rows'][block] = {
            'key': len(listed),
            'read': len(got),
            'exact': sum(1 for want, have in pairs if all(_same(have.get(k), v) for k, v in want.items())),
            'values': sum(len(want) for want in listed),
            'values_right': sum(sum(1 for k, v in want.items() if _same(have.get(k), v)) for want, have in pairs),
        }
    return out
