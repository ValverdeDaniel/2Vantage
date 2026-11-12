"""Revert of a questionnaire Activity row (plan.md §3.7, O.3.2; G123, E88). Registered as
`activity.reverters['questionnaire']` in QuestionnaireConfig.ready().

`deals.activity.revert` has already locked the Deal; this locks the form's row and hands the change to its owner:
answers (`services.answers.revert`), rows (`services.rows.revert`) and marks (`services.marks.revert`). A keys-only
row (sensitive answers) never gets here: Activity refuses it with its own sentence. Signatures and reopens are not
reverted (Reopen is the door). Returns the changes it wrote, which the revert row records.
"""

from deals import activity

from .models import Questionnaire
from .selectors import context
from .services import answers, common, marks, rows

DOORS = {'answers': answers.revert, 'rows': rows.revert, 'marked': marks.revert}


def revert(row_activity, user):
    door = DOORS.get(row_activity.action)
    target = next((entry['t'] for entry in row_activity.changes), '')
    questionnaire_id = target.split(':')[1] if target.startswith('questionnaire:') else ''
    if door is None or not questionnaire_id.isdigit():
        raise activity.Refused(activity.NO_REVERTER)
    row = Questionnaire.objects.select_for_update().filter(pk=int(questionnaire_id)).first()
    if row is None:
        raise activity.Refused(activity.NOTHING_TO_PUT_BACK)
    if row.locked and row_activity.action != 'answers':
        raise activity.Refused(common.LOCKED)
    row, written = door(row_activity, user, row)
    common.restamp(row, context.prefill_facts(row.deal))
    row.save()
    return [activity.change(common.target(row), written)]
