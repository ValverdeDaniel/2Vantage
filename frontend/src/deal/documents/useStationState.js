import { useLocation, useSearchParams } from 'react-router';

/*
 * The Documents station's state in the URL (plan.md §8.1 routes, O.4; E2, E3, E18, E31, D-164): `?doc=` the file on
 * screen (an id, or `proposals` for 📚 All proposals), `?ref=` the value being shown ("plan:41:rate_ee"; never the
 * value itself, which can be census data, Q.8), `?page=` a page to open, `?back=` where "‹ Back to review" returns,
 * and `?list=` the Scanned data panel's scope when it is not the viewer's file: `proposals` (every proposal file) or a
 * file id. F, or Review mode following a value (E65), moves the viewer to the value's own file; the List or the Grid,
 * its pick and its scroll stay on their files (D-164, D129). Each navigation has its own key, so a second ↗ on the
 * same value finds it again (`jumpKey`).
 */
export const ALL_PROPOSALS = 'proposals';

export default function useStationState() {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const back = params.get('back') || '';

  /** Show a file: the value and page it was opened for go (E2); a way back stays. */
  function select(docId) {
    const next = new URLSearchParams({ doc: String(docId) });
    if (back) next.set('back', back);
    setParams(next);
  }

  /**
   * Open one value in its file (F, Enter, a double-click on the List, a click in Review mode). `list` keeps the
   * Scanned data on its scope; `ref` '' shows the file with no value boxed (a blank cell in Review), on `page`.
   * `replace` (Review's following) keeps the browser's history to one entry per visit.
   */
  function show(docId, ref, { list = '', page = '', replace = false } = {}) {
    const next = new URLSearchParams({ doc: String(docId) });
    if (ref) next.set('ref', ref);
    if (page) next.set('page', String(page));
    if (list) next.set('list', String(list));
    if (back) next.set('back', back);
    setParams(next, { replace });
  }

  return {
    doc: params.get('doc') || '',
    ref: params.get('ref') || '',
    page: params.get('page') || '',
    list: params.get('list') || '',
    back,
    jumpKey: location.key,
    select,
    show,
  };
}
