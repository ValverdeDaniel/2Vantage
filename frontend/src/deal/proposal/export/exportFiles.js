/*
 * The Export viewer's files (plan.md §8.14; J105, F136; the old ExportViewer FORMATS and AdvisorTab EXPORT_FILES at
 * 891f1b3): Excel, PowerPoint, Paper and PDF, in the 2026-11-05 call's order (the "Web form" chip is dropped, J106).
 * `live` files have a view; the others show greyed with "next" until their view is built — the PowerPoint, Paper
 * and PDF pages are slice 30's deck view, one build behind the three. `?file=` picks one on landing, else the one
 * picked last in this browser, else the spreadsheet. Pure.
 */

export const FILES = [
  { id: 'excel', label: 'Excel', live: true, title: 'The client spreadsheet, tab by tab' },
  { id: 'powerpoint', label: 'PowerPoint', live: false, title: 'The client PowerPoint, slide by slide' },
  { id: 'paper', label: 'Paper', live: false, title: 'The client PDF on US Letter, page by page as it prints' },
  { id: 'pdf', label: 'PDF', live: false, title: 'The client PDF, page by page as it downloads' },
];
export const DEFAULT_FILE = 'excel';

/** The file to show: the wanted one (the URL's, else the kept one) when it has a view; else the spreadsheet. */
export function chooseFile(wanted, files = FILES) {
  return files.some((file) => file.id === wanted && file.live) ? wanted : DEFAULT_FILE;
}

/** "Built 2:05 PM · 13 tabs" for a copy built at `iso`, or '' while there is none. */
export function builtWords(iso, count, noun) {
  if (!iso) return '';
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return '';
  const time = when.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  return `Built ${time} · ${count} ${noun}${count === 1 ? '' : 's'}`;
}

/**
 * What a preview's error means (J107: a refusal and a failure are shown apart): the download's own sentence for a
 * refusal (409), which replaces the copy; a failure keeps the last copy on screen.
 */
export function previewError(error) {
  if (!error) return { refused: '', failed: '' };
  const status = error.response?.status;
  const detail = error.response?.data?.detail;
  if (status === 409 && typeof detail === 'string') return { refused: detail, failed: '' };
  return { refused: '', failed: 'Could not build the preview.' };
}
