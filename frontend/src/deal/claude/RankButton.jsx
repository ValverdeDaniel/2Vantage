import { useSyncExternalStore } from 'react';
import { useSearchParams } from 'react-router';
import { useStartRank } from '../../api/ai';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { subscribe, viewOf } from '../shared/boardBridge';
import { rankLabel, rankScope, rankTitle } from './rankWords';

/*
 * ⚖ Rank plans in the client guidance box (plan.md §8.17, §10.4; D6, D96, F111, OQ44; slice 37; the old WorkWithClaude
 * `advisor-rank` button): Claude stars the 5–8 quoted plans of the board's line that best fit the guidance, each with
 * its reason, within the line's room. On a filtered board it says "⚖ Rank filtered (N)" and ranks only those plans:
 * stars outside the filter stay (OQ44). Off, with its reason as the title, without guidance ("Add client guidance
 * first"), on a locked table, or while a rank runs ("Ranking…" and its last step). Where it lands is the strip's: the
 * stars, with ↶ Undo this run.
 */
export default function RankButton({ dealId, guidance, state, model }) {
  const toast = useToast();
  const [params] = useSearchParams();
  const board = useSyncExternalStore(subscribe, () => viewOf(dealId));
  const start = useStartRank(dealId);
  const scope = rankScope(board, params.get('line') || '');
  const running = (state?.jobs || []).find((job) => job.kind === 'rank');
  const locked = Boolean(state?.lock);
  const ranking = Boolean(running) || start.isPending;

  async function press() {
    try {
      await start.mutateAsync({ line: scope.line, planIds: scope.planIds, model });
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        data-guide="advisor-rank"
        onClick={press}
        disabled={ranking || !guidance || locked || !scope.line}
        title={rankTitle({ locked, guidance, scope })}
      >
        {rankLabel(scope, ranking)}
      </button>
      {running?.step && (
        <span className="bnf-extract-line bb-mono">
          <span className="bb-dot-pulse" /> {running.step}
        </span>
      )}
    </>
  );
}
