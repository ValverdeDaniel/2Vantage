import { useState } from 'react';
import { useSearchParams } from 'react-router';
import { useMeta } from '../../../api/meta';
import * as q from '../../../api/quotes';
import InlineError from '../../../ui/InlineError';
import Loading from '../../../ui/Loading';
import BoardDialogs from '../BoardDialogs';
import EnrollmentPanel from '../enrollment/EnrollmentPanel';
import PresentedGrid from './PresentedGrid';
import { pickLine } from './presentedModel';

/*
 * The Advisor's board in presented mode (plan.md §8.15; J70–J94, ch31), what the Proposal tab shows under its packet
 * card: the route mounts it (pages/DealPage/ProposalRoute.jsx), so the proposal folder never imports this one. Its
 * line lives in the URL (`?line=`); its data is the Advisor's own ['deal', id, 'advisor', …] queries, staleTime 0,
 * so a write on either tab shows on the other. The counts card and the census and split notices are the Advisor's
 * (J83); its dialogs (＋ Add plan, the template import, change history) too.
 */
export default function PresentedBoard({ deal }) {
  const { data: meta } = useMeta();
  const [params, setParams] = useSearchParams();
  const lines = q.useAdvisorLines(deal.id);
  const line = pickLine(lines.data, params.get('line'));
  const comparison = q.useComparison(deal.id, line);
  const [dialog, setDialog] = useState(null);
  const onLine = (next) =>
    setParams(
      (now) => {
        const out = new URLSearchParams(now);
        out.set('line', next);
        return out;
      },
      { replace: true },
    );

  if (lines.isPending || !meta) return <Loading label="Loading the plan comparison…" />;
  if (lines.isError) return <InlineError title="Plan comparison" error={lines.error} onRetry={() => lines.refetch()} />;
  if (!line) {
    return (
      <div className="bb-panel">
        <div className="bb-panel-title">No plans to compare yet</div>
        <div className="bb-panel-sub">Add the carrier quotes in the Advisor; the comparison and the proposal follow.</div>
      </div>
    );
  }
  const data = comparison.data;
  if (!data && comparison.isError) {
    return <InlineError title="Plan comparison" error={comparison.error} onRetry={() => comparison.refetch()} />;
  }
  if (!data) return <Loading label="Loading the plan comparison…" />;
  const counts = dialog?.kind === 'counts';
  const lineLabel = meta.lines.find((entry) => entry.key === line)?.label ?? line;
  return (
    <>
      <PresentedGrid
        deal={deal}
        meta={meta}
        lines={lines.data}
        line={line}
        onLine={onLine}
        data={data}
        onDialog={setDialog}
        enrollment={
          <EnrollmentPanel
            dealId={deal.id}
            meta={meta}
            line={line}
            lineLabel={lineLabel}
            data={data}
            open={counts}
            preselect={dialog?.preselect}
            onOpen={() => setDialog({ kind: 'counts' })}
            onClose={() => setDialog(null)}
          />
        }
      />
      <BoardDialogs dealId={deal.id} line={line} comparison={data} dialog={dialog} onDialog={setDialog} />
    </>
  );
}
