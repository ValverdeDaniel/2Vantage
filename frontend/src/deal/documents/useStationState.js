import { useLocation, useSearchParams } from 'react-router';

/*
 * The Documents station's state in the URL (plan.md §8.1 routes, O.4; E2, E3, E18): `?doc=` the file on screen (an id,
 * or `proposals` for 📚 All proposals), `?ref=` the value being shown ("plan:41:rate_ee"; never the value itself,
 * which can be census data, Q.8), `?page=` a page to open, `?back=` where "‹ Back to review" returns. Each navigation
 * has its own key, so a second ↗ on the same value finds it again (`jumpKey`).
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

  return {
    doc: params.get('doc') || '',
    ref: params.get('ref') || '',
    page: params.get('page') || '',
    back,
    jumpKey: location.key,
    select,
  };
}
