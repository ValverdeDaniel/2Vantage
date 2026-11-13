"""/api/meta/ `agenda` (plan.md §7.1; I.6): the Agenda's words and constants, so the browser hard-codes none (rule 1).
The Work queue's due buckets, type chips and categories join with it in slice 61."""

from . import catalogue, rules


def meta():
    return {
        'sections': catalogue.SECTIONS,
        'collapsed': list(catalogue.COLLAPSED),
        'steps': [
            {'key': key, 'title': title, 'tab': tab, 'track': track, 'lead': lead}
            for key, (title, tab, track, lead) in catalogue.STEPS.items()
        ],
        'owner_words': catalogue.OWNER_WORDS,
        'follow_up_days': rules.FOLLOW_UP_DAYS,
        'later_picks': rules.LATER_PICKS,
        'soon_days': rules.SOON_DAYS,
        'follow_up_kinds': [{'key': rules.CALL, 'label': 'Called'}, {'key': rules.EMAIL, 'label': 'Emailed'}],
        'milestones': [{'key': key, 'label': label, 'group': group} for key, label, group in catalogue.MILESTONES],
        'groups': catalogue.GROUP_LABELS,
        'title_max': rules.TITLE_MAX,
        'note_max': rules.TASK_NOTE_MAX,
        'mark_note_max': rules.MARK_NOTE_MAX,
    }
