import { useEffect, useLayoutEffect, useRef, useSyncExternalStore } from 'react';
import { pickOf, register, setPick, subscribe } from '../../shared/boardBridge';
import { clearFilters } from './boardConfig';

/*
 * The board's half of Work with Claude's bridge (plan.md §10.6; D80, F25, F108; the old AdvisorTab boardApi): while
 * the quote board is on screen it tells the drawer what it shows (its line, config, the plans drawn and Claude's
 * pick), and it applies a turn's set_board patch: the line first, then the config over what is set now — or over no
 * filters when the patch clears — through `useBoardConfig`'s `set`, so the URL holds it like any other filter
 * (§3.9), then the pick. A patch that arrived while the Advisor was off screen is applied when the board mounts.
 */
export default function useBoardBridge({ dealId, line, onLine, view, boardMeta, shownIds, total }) {
  const latest = useRef(null);
  useLayoutEffect(() => {
    latest.current = { line, onLine, view, boardMeta, shownIds, total };
  });

  useEffect(
    () =>
      register(dealId, {
        get: () => {
          const now = latest.current;
          return { line: now.line, config: now.view.config, shown_ids: now.shownIds, total: now.total, pick: pickOf(dealId) };
        },
        apply: (patch) => {
          const now = latest.current;
          if (patch.line && patch.line !== now.line) now.onLine(patch.line);
          const config = patch.config || {};
          now.view.set((current) => (patch.clear ? { ...clearFilters(current, now.boardMeta), ...config } : config));
          if ('pick' in patch) setPick(dealId, patch.pick);
          else if (patch.clear) setPick(dealId, null);
        },
      }),
    [dealId],
  );
}

/** Claude's pick on this deal, if it was judged on `line` (F25: one line only). */
export function usePick(dealId) {
  return useSyncExternalStore(subscribe, () => pickOf(dealId));
}
