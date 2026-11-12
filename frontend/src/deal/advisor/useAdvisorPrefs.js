import { useState } from 'react';
import { useSearchParams } from 'react-router';
import {
  VIEWS,
  chooseFileWanted,
  chooseLayout,
  chooseLine,
  chooseOrientation,
  chooseView,
  offeredViews,
  readPrefs,
  writePrefs,
} from './advisorPrefs';

const storage = () => (typeof window === 'undefined' ? null : window.localStorage);

/*
 * The Advisor's view, line and layout (plan.md §8.14; F1, F5, F34; `advisorPrefs.js` holds the rules). `?view=` and
 * `?line=` win; a pick is kept in this browser and written to the URL (in-tab state lives in the query string,
 * §3.9), replacing the entry so Back leaves the tab. `quoted` is the deal's printed tables (undefined while they load,
 * when "As quoted" stays chosen rather than falling back for a moment). The Export viewer's file works the same way
 * through `?file=` (F136; slice 28); `openExport` picks the view and the file at once (J58; slice 30), `openLine` the
 * Quote comparison and a line (slice 36). `stopLossLine` (meta's `stop_loss.line`) offers the Stop-loss pill (F2).
 */
export default function useAdvisorPrefs(lines, quoted, stopLossLine) {
  const [params, setParams] = useSearchParams();
  const [kept, setKept] = useState(() => readPrefs(storage()));
  const offered = offeredViews(lines, quoted, stopLossLine);
  const view = chooseView(params.get('view'), kept.view, quoted === undefined ? VIEWS : offered);
  const line = chooseLine(params.get('line'), kept.line, lines);
  const orientation = chooseOrientation(kept.orientation);
  const layout = chooseLayout(kept.layout);
  const file = chooseFileWanted(params.get('file'), kept.exportFile);

  // One URL write for everything a pick changes: two in a row would each start from the same URL.
  const remember = (patch, url = {}) => {
    writePrefs(storage(), patch);
    setKept((now) => ({ ...now, ...patch }));
    if (Object.keys(url).length) {
      setParams(
        (now) => {
          const next = new URLSearchParams(now);
          Object.entries(url).forEach(([key, value]) => next.set(key, value));
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
    layout,
    file,
    pickView: (next) => remember({ view: next }, { view: next }),
    pickFile: (next) => remember({ exportFile: next }, { file: next }),
    // The Export viewer on one file ("See the slides ▸", J58: `?view=export&file=powerpoint`).
    openExport: (file) => remember({ view: 'export', exportFile: file }, { view: 'export', file }),
    pickLine: (next) => remember({ line: next }, { line: next }),
    // Quote comparison on one line (the stop-loss board's empty state sends you to the Stop-Loss line; slice 36).
    openLine: (next) => remember({ view: 'quotes', line: next }, { view: 'quotes', line: next }),
    pickOrientation: (next) => remember({ orientation: next }),
    pickLayout: (next) => remember({ layout: next }),
  };
}
