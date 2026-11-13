/* The Agenda's pure view logic (I.6 `rowView.js`): days measured from the payload's `today` (the agency's date, never
   the browser's: I.5 bug 1), the sections in meta's order, each row's detail words and its buttons from the server's
   `can` flags. Words from old Vantage 891f1b3 `shared/agenda/AgendaParts.jsx` and `agendaRows.js`. React-free. */

const DAY = 86400000;

function utc(iso) {
  if (!iso) return null;
  const day = new Date(`${String(iso).slice(0, 10)}T00:00:00Z`);
  return Number.isNaN(day.getTime()) ? null : day;
}

/** The ISO day `days` after `today` (YYYY-MM-DD), counted on the calendar, never across a time zone. */
export function isoIn(today, days = 0) {
  const day = utc(today);
  return day ? new Date(day.getTime() + days * DAY).toISOString().slice(0, 10) : '';
}

/** "Nov 20, 2026": the old row date and "Back …" words (clientMath.dayLabel(iso, true)). */
export function dayLabel(iso) {
  const day = utc(iso);
  if (!day) return '';
  return day.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
}

/** Later's picks from `today` (Tomorrow, In 3 days, Next week), less any past the row's `later_max` (I15, ch. 25). */
export function laterPicks(meta, today, max) {
  return (meta?.agenda?.later_picks || [])
    .map((pick) => ({ label: pick.label, until: isoIn(today, pick.days) }))
    .filter((pick) => !max || pick.until <= max);
}

/** [{key, title, sub, empty, rows}] in the sections' order (I4); rows keep the server's order (I6). */
export function sectionsOf(payload, meta) {
  const rows = payload?.rows || [];
  return (meta?.agenda?.sections || []).map((section) => ({
    ...section,
    rows: rows.filter((row) => row.section === section.key),
  }));
}

function ownerWords(meta, owner) {
  return meta?.agenda?.owner_words?.[owner] || 'someone';
}

/** The words under a row's label (I11). */
export function detailOf(row, meta) {
  if (row.kind === 'task') {
    const done = row.done ? `Done${row.done_by ? ` by ${row.done_by}` : ''}` : '';
    const who = row.assigned_to ? `For ${row.assigned_to.name}` : '';
    return [done || who, row.note].filter(Boolean).join(' — ');
  }
  if (row.kind !== 'step') return '';
  if (row.later_until) {
    const by = row.later?.by ? ` · ${row.later.by}` : '';
    const note = row.later?.note ? ` — ${row.later.note}` : '';
    return `Back ${dayLabel(row.later_until)}${by}${note}`;
  }
  if (row.done_anyway) return `Marked done${row.done_anyway.by ? ` by ${row.done_anyway.by}` : ''}`;
  if (row.state === 'blocked') return row.blocked_reason || '';
  if (row.state === 'waiting') return `Waiting on ${ownerWords(meta, row.owner)}`;
  return '';
}

/** The buttons a row offers, in the old order, from its `can` flags: [{key, label, title, tick}]. */
export function actionsOf(row) {
  const can = row.can || {};
  if (row.kind === 'step') {
    if (can.bring_back) return [{ key: 'bring_back', label: 'Bring back', title: 'Put it back on the Agenda now' }];
    if (can.undo) return [{ key: 'undo', label: 'Undo', title: 'Take back "Done anyway"' }];
    const out = [];
    if (can.later) out.push({ key: 'later', label: 'Later', title: 'Bring it back on a day you pick' });
    if (can.follow_up) {
      out.push({ key: 'follow_up', label: 'Log follow-up', title: 'Record the call or email; it waits again after' });
    } else if (can.done_anyway) {
      out.push({ key: 'done_anyway', label: 'Done anyway', title: 'Count it done although the system still sees it open' });
    }
    return out;
  }
  const out = [];
  if (can.reopen) out.push({ key: 'reopen', label: '↺', title: 'Reopen this task', tick: true });
  if (can.later) out.push({ key: 'later', label: 'Later', title: 'Move it to a day you pick' });
  if (row.kind === 'task' && can.edit) out.push({ key: 'edit', label: 'Edit', title: 'Change this task' });
  if (row.kind === 'task' && can.delete) out.push({ key: 'delete', label: 'Delete', title: 'Delete this task' });
  if (can.tick) out.push({ key: 'tick', label: '✓', title: 'Mark this task done', tick: true });
  return out;
}

/** A row's severity dot: done rows are green, otherwise the server's (I10, I30). */
export function dotOf(row) {
  if (row.section === 'done') return 'done';
  return row.severity || 'info';
}
