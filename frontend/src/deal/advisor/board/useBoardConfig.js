import { useLayoutEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router';
import { clearFilters, fromSaved, readConfig, writeConfig } from './boardConfig';

/*
 * The board's config in the URL (plan.md §3.9; boardConfig.js holds the rules): read from the query string on every
 * render, written back with `replace` so typing in the finder never fills the history. Two writes before the next
 * render (a quick second edit) build on each other: the router's own updater would hand both the same starting URL.
 * The layout is the one setting kept per browser (⇄ Transpose, F34): it comes from the Advisor's prefs and a saved
 * setup sets it there.
 *   set(patch | config => patch) · apply(saved config) · clear() — Claude's set_board (slice 24) calls `set`.
 */
export default function useBoardConfig(board, prefs) {
  const [params, setParams] = useSearchParams();
  const layout = prefs.orientation;
  const config = useMemo(() => readConfig(params, board, layout), [params, board, layout]);
  const latest = useRef(params);
  useLayoutEffect(() => {
    latest.current = params;
  }, [params]);

  const write = (next) => {
    const written = writeConfig(latest.current, next(readConfig(latest.current, board, layout)), board);
    latest.current = written;
    setParams(written, { replace: true });
  };

  return {
    config,
    set: (patch) => write((now) => ({ ...now, ...(typeof patch === 'function' ? patch(now) : patch) })),
    apply: (saved) => {
      const next = fromSaved(saved, board, layout);
      write(() => next);
      if (next.layout !== layout) prefs.pickOrientation(next.layout);
    },
    clear: () => write((now) => clearFilters(now, board)),
  };
}
