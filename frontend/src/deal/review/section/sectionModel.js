// The section bar's numbers and words (plan.md §8.8; L14, C34; old 891f1b3 `SectionReviewBar.jsx` `sectionNumbers`,
// `reviewrequest/ReviewSectionBar.jsx`). Pure, over one section of the Board payload's `sections` (the deal page's one
// count, so the bar, the lanes and the pills cannot disagree).

/**
 * The three lane counts and the tray's: to review (ready answers and questions), waiting on the client (still typing,
 * and answers sent back and not answered since: slice 56's going back, as the old bar counted them), missing.
 */
export function sectionNumbers(section) {
  const found = section || {};
  return {
    review: (found.to_review || 0) + (found.questions || 0),
    waiting: (found.in_progress || 0) + (found.going_back || 0),
    missing: found.missing || 0,
    inTray: found.in_tray || 0,
  };
}

/** What came back, for the violet line and "Approve N ready ✓". */
export function returnedOf(section) {
  const found = section || {};
  return {
    names: found.names || [],
    answered: (found.to_review || 0) + (found.in_progress || 0),
    ready: found.ready || 0,
    readySubmitted: found.ready_submitted ?? found.ready ?? 0,
    readyIdle: found.ready_idle || 0,
    typing: found.in_progress || 0,
    questions: found.questions || 0,
  };
}

/** "Dana", "Dana and Lee", "Dana, Lee and 2 more"; nobody named is "The client". */
export function whoOf(names) {
  const list = (names || []).filter(Boolean);
  if (!list.length) return 'The client';
  if (list.length === 1) return list[0];
  if (list.length === 2) return `${list[0]} and ${list[1]}`;
  return `${list[0]}, ${list[1]} and ${list.length - 2} more`;
}

const plural = (n, one) => `${n} ${n === 1 ? one : `${one}s`}`;

/** "↩ Dana answered 3 · 2 ready · 1 still typing · 1 question", or "↩ Dana asked 1 question". */
export function returnText(returned) {
  const who = whoOf(returned.names);
  if (!returned.answered) return `↩ ${who} asked ${plural(returned.questions, 'question')}`;
  const rest = Math.max(0, returned.answered - returned.ready - returned.typing);
  return [
    `↩ ${who} answered ${returned.answered}`,
    returned.ready > 0 && `${returned.ready} ready`,
    returned.typing > 0 && `${returned.typing} still typing`,
    rest > 0 && `${rest} to look at`,
    returned.questions > 0 && plural(returned.questions, 'question'),
  ]
    .filter(Boolean)
    .join(' · ');
}

/** How many "Approve N ready ✓" takes: the submitted answers, and an idle link's too with the tick. */
export function taking(returned, withIdle) {
  return returned.readySubmitted + (withIdle ? returned.readyIdle : 0);
}
