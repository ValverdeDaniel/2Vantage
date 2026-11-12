import { summaryOf } from './queueWords';

// Why X cannot act yet: a send-back is a note in the request tray, which arrives with slice 56 (L22, L49–L53).
export const SEND_BACK_LATER =
  'Sending an answer back to the client goes through the request tray, which comes in a later version. For now, keep ' +
  'ours (U) or correct it (E).';

/** A row's title, sub-line, change chip and flag (old renderSummary; "blocks Aetna", "required to market"). */
export function renderSummary(item, changes) {
  const summary = summaryOf(item);
  const badge = <span className={`rr-change-chip rr-change-${item.change}`}>{changes[item.change] || item.change}</span>;
  const flag = summary.flag || (item.required ? 'required to market' : '');
  return { ...summary, badge, flag };
}

/** What A, X, E and U do on an item (old cfgFor): approve, send back (later), correct it ourselves, keep ours. */
export function cfgFor(item) {
  const person = item.kind === 'person';
  const theirs = Array.isArray(item.theirs) ? '' : item.theirs || '';
  return {
    approve: person ? 'Add to census' : 'Approve',
    reject: 'Send back',
    rejectBlocked: SEND_BACK_LATER,
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
