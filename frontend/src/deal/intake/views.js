/*
 * The Intake tab's views, Form · Board · Request · Review (plan.md §8.9; B36). Pure. `?view=` is read from the URL on
 * every render and written on a click; a bare tab, or a view not built yet, is the Form. Board, Request and Review are
 * the Review app's components scoped to intake (Part L, slices 53–57).
 */
export const VIEWS = [
  { key: 'form', label: 'Form', title: 'The intake form: every answer, as we hold it' },
  { key: 'board', label: 'Board', title: 'What the intake is missing, waiting on and has to review, in three lanes' },
  {
    key: 'request',
    label: 'Request',
    title: 'What to ask the client about the intake, the form they get and what waits on you',
  },
  { key: 'queue', label: 'Review', title: 'The client’s answers and the AI’s reads on the intake, one at a time' },
];
export const BUILT = new Set(['form']);
export const LATER = 'Arrives with Review & requests';

/** The view the URL names, else the Form. */
export function viewOf(params) {
  const view = params.get('view');
  return BUILT.has(view) ? view : 'form';
}
