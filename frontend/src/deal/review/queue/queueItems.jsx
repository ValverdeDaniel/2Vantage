import { summaryOf } from './queueWords';

// Why X cannot send a person back: a person the client added is added or kept off whole (Ch. 12).
export const NOT_A_PERSON = 'A person the client added is added to the census or kept off whole: X sends values back, not people.';
// Why only Approve is offered on a signed form (slice 58, G70): the officer attested these answers.
export const SIGNED_FORM = 'The company officer signed this form with these answers: reopen it on the Questionnaire tab to change one.';

/** A row's title, sub-line, change chip and flag (old renderSummary; "blocks Aetna", "required to market"). */
export function renderSummary(item, changes) {
  const summary = summaryOf(item);
  const badge = <span className={`rr-change-chip rr-change-${item.change}`}>{changes[item.change] || item.change}</span>;
  const flag = item.question_open
    ? '? question open'
    : summary.flag || (item.signed ? 'signed by the officer' : item.required ? 'required to market' : '');
  return { ...summary, badge, flag };
}

/**
 * What A, X, N, E and U do on an item (old cfgFor): approve; send back with a note — into the request tray, sent from
 * the request page (L17, L22; slice 56); a team note that leaves it where it is; correct it ourselves; keep ours.
 */
export function cfgFor(item) {
  const person = item.kind === 'person';
  const theirs = Array.isArray(item.theirs) ? '' : item.theirs || '';
  if (item.signed) {
    // A signed form's answers are approved as they were attested, or the form is reopened (slice 58).
    return { approve: 'Approve', reject: 'Send back', rejectMode: 'note', rejectBlocked: SIGNED_FORM, noteAction: '＋ Note', extras: [] };
  }
  return {
    approve: person ? 'Add to census' : 'Approve',
    reject: 'Send back',
    rejectMode: 'note',
    rejectBlocked: person ? NOT_A_PERSON : '',
    noteLabel: 'Back to the client, with a note',
    notePh: 'What should they check? Leave it blank for “Please check this and update it.”',
    noteRequired: false,
    noteAction: '＋ Note',
    extras: [
      ...(item.editable
        ? [
            {
              action: 'correct',
              label: 'Correct',
              key: 'E',
              mode: 'value',
              title: 'type the right value yourself',
              valueLabel: `${item.label}: the right value`,
              valuePh: theirs,
              valueInit: theirs,
              blankAllowed: true,
            },
          ]
        : []),
      {
        action: 'clear',
        label: person ? 'Keep them off' : 'Keep ours',
        key: 'U',
        title: person ? 'they stay off the census' : 'what we hold stays; their answer is set aside',
      },
    ],
  };
}
