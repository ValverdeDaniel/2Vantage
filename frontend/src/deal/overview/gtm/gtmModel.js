// Card 1 and Card 2's pure rules (plan.md §8.6; M42–M62, M65; old Vantage 891f1b3 `GetToMarketCard.jsx`,
// `PhaseCards.jsx`). The groups, their words and what each row is come from the server (`get_to_market`,
// `quote_to_close`); these decide only what the browser holds: which groups are open, where a link goes, which rows
// offer "＋ Ask", and how Card 2's rows meet the journey's steps. Vitest pins them (gtmModel.test.js).

// The two rows that carry an in-app form: once a fillable form is chosen, their ask is the form itself, to fill
// online (slice 58's `qform:` ask, not built here yet); with no fillable form ("upload only") they ask for the file.
const FORM_ITEMS = new Set(['medical_questionnaire', 'stop_loss_disclosure']);

/** A group stays open until it is met, then the person's own toggle wins (M44). */
export function isOpen(group, toggled) {
  return toggled[group.key] !== undefined ? toggled[group.key] : !group.met;
}

/** The toggles after a click on `group`'s head. */
export function toggled(state, group) {
  return { ...state, [group.key]: !isOpen(group, state) };
}

/** `/deals/7/census` or `/deals/7/review?section=census&lane=missing`. */
export function tabLink(dealId, tab, params = {}) {
  const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value != null && value !== ''));
  const tail = query.toString();
  return `/deals/${dealId}/${tab}${tail ? `?${tail}` : ''}`;
}

/** The request-tray ref a missing document row asks for (`doc:<kind>`), else null (M54): a form row asks for its file
 *  only while no fillable form is chosen (the form's own ask is slice 58's). */
export function askRefOf(item) {
  if (item.satisfy !== 'document' || item.status !== 'missing' || !item.kind) return null;
  if (FORM_ITEMS.has(item.key) && item.form_key) return null;
  return `doc:${item.kind}`;
}

/** The words after a row's label: a file on hand or the form signed (old `— document on file`, `— on file`). */
export function suffixOf(item, { form = false } = {}) {
  if (form && item.signed) return ' — signed';
  if (item.has_document) return form ? ' — document on file' : ' — on file';
  return '';
}

/** Where a form group's "Open questionnaire ▸" / "Open disclosure ▸" goes (M108, M109), or null with no form. */
export function formLink(dealId, group) {
  const key = group.item?.form_key;
  if (!key) return null;
  if (group.key === 'stop_loss') return { label: 'Open disclosure ▸', to: tabLink(dealId, 'questionnaire', { form: key }) };
  return { label: 'Open questionnaire ▸', to: tabLink(dealId, 'questionnaire') };
}

/** Card 1's main footer button (M61): Send to market once ready, else Open intake. */
export function marketButton(dealId, card) {
  if (card.badge === 'ready') return { label: 'Send to market ▸', to: tabLink(dealId, 'intake', { focus: 'marketed' }) };
  return { label: 'Open intake ▸', to: tabLink(dealId, 'intake') };
}

/**
 * Card 2's rows (M62): the journey's Quote to Close steps, in its order, with their state (done, current, todo), each
 * with the server's detail. Without the journey yet, the server's rows show as to do.
 */
export function quoteRows(journey, rows) {
  const details = Object.fromEntries((rows || []).map((row) => [row.key, row]));
  const module = (journey?.journey?.modules || []).find((found) => found.key === 'quote_to_close');
  const steps = module?.steps || (rows || []).map((row) => ({ key: row.key, label: '', state: 'todo' }));
  return steps.map((step) => ({
    key: step.key,
    label: step.label,
    state: step.state,
    detail: details[step.key]?.detail || '',
    at: details[step.key]?.at || null,
  }));
}
