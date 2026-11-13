// The client Agenda's pure view logic (plan.md §8.5; CL24; old Vantage 891f1b3 `radar/client/ClientAgendaTab.jsx`): a
// deal panel's title and line, the deal pick's words, which deals the Add form offers, and the Done panel's rows (the
// hand tasks and nudges ticked on the client's deals; reminders and client tasks wait, I104–I108). React-free; every
// date is the server's ISO day, shown with the app's formatDate.
import { stageLabel } from '../../../api/meta';
import { formatDate } from '../../../lib/format';

// The sections each deal panel shows (the old `sections={['upNext', 'waiting', 'later']}`).
export const PANEL_SECTIONS = ['up_next', 'waiting', 'later'];

const HAND = ['task', 'nudge'];

/** "Deal renewing 01/01/2027 · Sold" (old panel title; "Deal" alone with no effective date). */
export function panelTitle(deal, meta) {
  const head = deal.effective_date ? `Deal renewing ${formatDate(deal.effective_date)}` : 'Deal';
  const stage = stageLabel(meta, deal.stage);
  return stage ? `${head} · ${stage}` : head;
}

/** The panel's line: what it holds, then "Next: <the next step>." when the deal has one. */
export function panelSub(panel) {
  const next = panel.next_step?.label;
  return `What the deal needs now, and what it is waiting on.${next ? ` Next: ${next}.` : ''}`;
}

/** The deal pick's option: "On the deal renewing 01/01/2027 (Sold)" (old words). */
export function pickLabel(deal, meta) {
  const when = deal.effective_date ? ` renewing ${formatDate(deal.effective_date)}` : '';
  const stage = stageLabel(meta, deal.stage);
  return `On the deal${when}${stage ? ` (${stage})` : ''}`;
}

/** The deal a new task lands on: the one picked, else the first panel's; null with no deal. The pick shows only with
 *  two or more deals (§8.5). */
export function taskTarget(panels, picked) {
  const ids = (panels || []).map((panel) => panel.deal.id);
  if (!ids.length) return null;
  return ids.includes(Number(picked)) ? Number(picked) : ids[0];
}

/** [{deal, rows}] of the ticked hand tasks and nudges per deal, each offering only ↺ (the old Done panel's rows). */
export function doneRows(panels) {
  return (panels || [])
    .map((panel) => ({
      deal: panel.deal,
      rows: panel.rows
        .filter((row) => row.section === 'done' && HAND.includes(row.kind))
        .map((row) => ({ ...row, can: { reopen: Boolean(row.can?.reopen) } })),
    }))
    .filter((entry) => entry.rows.length > 0);
}

/** "2 tasks done." */
export function doneWords(count) {
  return `${count} task${count === 1 ? '' : 's'} done.`;
}
