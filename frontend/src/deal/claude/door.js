// The one door to Work with Claude on a deal page (plan.md §8.17; D1, D3, D16, D37; the old CaseWorkspace's
// `openClaude` and `attachToClaude`). Work with Claude is mounted once, in the deal shell, so it stays open across
// tabs; any tab may open it on a kind ("＋ Add quotes") or hand it the files dropped on the tab, and they wait here
// until the drawer takes them. What the person dismissed and the model they picked last the visit. Memory only.
import { useSyncExternalStore } from 'react';

// Where Work with Claude shows (A25, D1): the strip over the tables Claude reads into, and the pill on the tabs it
// works over (the shell pads those tabs' content, `bnf-wwc-room`, so the pill never covers the last row).
export const STRIP_TABS = new Set(['advisor', 'proposal', 'census', 'questionnaire', 'intake']);
export const PILL_TABS = new Set(['overview', 'intake', 'census', 'questionnaire', 'advisor', 'proposal', 'documents']);

export function claudeRoom(tab) {
  return PILL_TABS.has(tab);
}

const EMPTY = { dealId: null, open: false, kind: '', byParam: false, files: [], dismissed: [], model: '' };
let state = EMPTY;
const listeners = new Set();

function set(changes) {
  state = { ...state, ...changes };
  listeners.forEach((listener) => listener());
}

function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export const claudeDoor = {
  /** A new deal on screen starts closed, with nothing waiting. */
  enter(dealId) {
    if (state.dealId !== Number(dealId)) set({ ...EMPTY, dealId: Number(dealId), model: state.model });
  },
  /** Open the drawer; `kind` is what an attached file is filed as ('' keeps the tab's). */
  open(kind = '', { byParam = false } = {}) {
    set({ open: true, byParam, ...(kind ? { kind } : {}) });
  },
  close() {
    set({ open: false, byParam: false });
  },
  /** The URL's `?claude=1` went: a drawer it opened closes; one a person opened stays (D3). */
  closeIfByParam() {
    if (state.byParam) set({ open: false, byParam: false });
  },
  setKind(kind) {
    set({ kind });
  },
  setModel(model) {
    set({ model });
  },
  /** Files dropped on a tab (D16): the drawer opens and takes them. */
  attach(files) {
    const list = Array.from(files || []);
    if (list.length) set({ open: true, files: [...state.files, ...list] });
  },
  /** The files waiting for the drawer, handed over once. */
  take() {
    const { files } = state;
    if (files.length) set({ files: [] });
    return files;
  },
  dismiss(id) {
    if (!state.dismissed.includes(id)) set({ dismissed: [...state.dismissed, id] });
  },
};

export function useClaudeDoor() {
  return useSyncExternalStore(subscribe, () => state);
}
