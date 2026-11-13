// Where one item stands with the request tray, for a "＋ Ask" outside the Review tab (plan.md §8.8; L54; B12; old
// 891f1b3 `trayRefs.js`, IntakeTab's per-row ask): waiting in the tray ("✓ In tray"), already with the client on a link
// they have ("Asked Oct 20"), or not asked ("＋ Ask"). Pure: the tray payload (`api/reviewTray.useTray`) and a ref.

/** {state: 'in_tray' | 'asked' | 'ask' | 'closed', at?, draftId?} for `ref`. 'closed': the deal asks its client nothing. */
export function trayState(tray, ref) {
  if (!tray) return { state: 'ask' };
  if (tray.asks_closed) return { state: 'closed' };
  const draft = (tray.items || []).find((item) => item.ref === ref);
  if (draft) return { state: 'in_tray', draftId: draft.id };
  const at = tray.out?.[ref];
  if (at) return { state: 'asked', at };
  return { state: 'ask' };
}

/** The refs among `refs` not in the tray and not with the client: what "＋ Ask N" / "＋ Ask all" would add. */
export function askable(tray, refs) {
  return (refs || []).filter((ref) => trayState(tray, ref).state === 'ask');
}

/** "Oct 20" */
export function askedOn(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
