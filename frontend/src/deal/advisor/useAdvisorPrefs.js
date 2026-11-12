import { useState } from 'react';
import { useSearchParams } from 'react-router';
import { chooseLine, chooseOrientation, chooseView, offeredViews, readPrefs, writePrefs } from './advisorPrefs';

const storage = () => (typeof window === 'undefined' ? null : window.localStorage);

/*
 * The Advisor's view, line and layout (plan.md §8.14; F1, F5, F34; `advisorPrefs.js` holds the rules). `?view=` and
 * `?line=` win; a pick is kept in this browser and written to the URL (in-tab state lives in the query string,
 * §3.9), replacing the entry so Back leaves the tab.
 */
export default function useAdvisorPrefs(lines) {
  const [params, setParams] = useSearchParams();
  const [kept, setKept] = useState(() => readPrefs(storage()));
  const offered = offeredViews(lines);
  const view = chooseView(params.get('view'), kept.view, offered);
  const line = chooseLine(params.get('line'), kept.line, lines);
  const orientation = chooseOrientation(kept.orientation);

  const remember = (patch, urlKey) => {
    writePrefs(storage(), patch);
    setKept((now) => ({ ...now, ...patch }));
    if (urlKey) {
      setParams(
        (now) => {
          const next = new URLSearchParams(now);
          next.set(urlKey, patch[urlKey]);
          return next;
        },
        { replace: true },
      );
    }
  };

  return {
    offered,
    view,
    line,
    orientation,
    pickView: (next) => remember({ view: next }, 'view'),
    pickLine: (next) => remember({ line: next }, 'line'),
    pickOrientation: (next) => remember({ orientation: next }),
  };
}
