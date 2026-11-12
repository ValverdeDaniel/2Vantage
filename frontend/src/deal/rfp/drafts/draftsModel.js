// The Emails card's words, pure (plan.md §8.12, §9.11; K57–K66, K120; old CarriersTab.jsx CarrierDrafts at 891f1b3).

/** The collapsed card's one line (K66): "Marked sent 1 of 3", or "No drafts yet". */
export function draftsSummary(drafts) {
  if (!drafts?.total) return 'No drafts yet';
  return `Marked sent ${drafts.sent_count} of ${drafts.total}`;
}

/** The sub-line under the title (K57): what the route makes, and that nothing is sent from here. */
export function routeWords(route) {
  const shape =
    route === 'direct'
      ? 'One draft per carrier, each with our cover page and only that carrier’s files.'
      : 'One draft to Warner Pacific’s quoting inbox, carrying the whole packet.';
  return `${shape} Nothing is sent from here: copy a draft or open it in Outlook, read it, and send it yourself.`;
}

/** The To cell's second line: the address, or "your rep" for a direct draft (OQ59), and who is copied (OQ65). */
export function toWords(draft) {
  return `${draft.to || 'your rep'}${draft.cc ? ` · cc ${draft.cc}` : ''}`;
}

/** What "Copy" puts on the clipboard (K62): the subject line and the body, ready to paste. */
export function copyText(draft) {
  return `Subject: ${draft.subject}\n\n${draft.body}`;
}

/** The drafts as a tick leaves them, before the server answers. */
export function optimisticSent(drafts, key, sent) {
  if (!drafts) return drafts;
  const rows = drafts.rows.map((draft) =>
    draft.key === key ? { ...draft, sent: sent ? { on: '', shown: '…', by: '' } : null } : draft,
  );
  return { ...drafts, rows, sent_count: rows.filter((draft) => draft.sent).length };
}

/** Whether the footer offers "Mark as marketed" (K33): something went out and the deal is not marked yet. */
export function offersMarketed(drafts, marketedAt) {
  return Boolean(drafts?.any_sent) && !marketedAt;
}
