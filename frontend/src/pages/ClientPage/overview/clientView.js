// The client Overview's words, worked out from the server's figures (plan.md §8.5; old ClientOverviewTab.jsx and
// ArtifactChips.jsx at 891f1b3). Pure: clientView.test.js pins it. No money math here (rule 5): amounts arrive
// rounded and are only printed.

/** "in 50d" / "today" is "in 0d" / "3d ago": the header chip's distance to the effective date. */
export function dayWords(days) {
  return days >= 0 ? `in ${days}d` : `${-days}d ago`;
}

/** The Effective tile: "50d" before the date, "3d ago" after (rose), "—" without one. */
export function effectiveTile(effective) {
  if (!effective) return { value: '—', tone: 'bb-empty' };
  if (effective.days >= 0) return { value: `${effective.days}d`, tone: '' };
  return { value: `${-effective.days}d ago`, tone: 'bb-rose' };
}

/** The Agenda tile (CL18; old Upkeep tile): "N overdue" rose, else "N soon" amber, else "clear" green. */
export function agendaTile(agenda) {
  const { overdue = 0, soon = 0, total = 0 } = agenda || {};
  if (overdue) return { value: `${overdue} overdue`, tone: 'bb-rose', total };
  if (soon) return { value: `${soon} soon`, tone: 'bb-amber', total };
  return { value: 'clear', tone: 'bb-green', total };
}

/**
 * A History row's chips (G116; old ArtifactChips): Intake while answers are on file, Census with its employees, each
 * carrier form ("✓" once signed), and the files; each with the tab it opens on the deal page and its tooltip.
 */
export function historyChips(row) {
  const { chips } = row;
  const year = row.year ? `${row.year} ` : '';
  const out = [];
  if (chips.intake) {
    out.push({
      key: 'intake',
      tab: 'intake',
      label: 'Intake',
      title: `${chips.intake.answered} of ${chips.intake.needed} intake answers on file — open the ${year}intake`,
    });
  }
  if (chips.census) {
    const { employees, dependents } = chips.census;
    out.push({
      key: 'census',
      tab: 'census',
      label: 'Census',
      count: `${employees} EE`,
      title: `${employees} employees${dependents ? ` and ${dependents} dependents` : ''} on file — open the ${year}census`,
    });
  }
  for (const form of chips.forms) {
    const state = form.signed ? 'signed' : form.started ? 'started, not signed' : 'not started';
    out.push({
      key: `form:${form.key}`,
      tab: `questionnaire?form=${encodeURIComponent(form.key)}`,
      label: `${form.chip}${form.signed ? ' ✓' : ''}`,
      done: form.signed,
      title: `${form.label} — ${state}. Open the ${year}form.`,
    });
  }
  if (chips.documents > 0) {
    out.push({
      key: 'documents',
      tab: 'documents',
      label: 'Docs',
      count: String(chips.documents),
      title: `${chips.documents} file${chips.documents === 1 ? '' : 's'} — open the ${year}documents`,
    });
  }
  return out;
}
