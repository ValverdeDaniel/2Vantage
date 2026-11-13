import { useEffect } from 'react';
import { useSearchParams } from 'react-router';
import { useMeta } from '../../api/meta';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import ClientsView from './ClientsView';
import FeedView from './FeedView';
import { readHome, stepsParams, viewParams } from './homeParams';

const TITLES = { prospects: 'Prospects', book: 'Clients', queue: 'Work queue' };

/**
 * The Benefits home (plan.md §8.3; CasesDashboard.jsx at 891f1b3): the eyebrow, then the view the pill picks.
 * Prospects (bare /, the landing view; OQ95 as reworded by OQ101 c) and the Work queue (?view=queue; slice 61) read the
 * one work feed; Clients (?view=book) lists New and Existing clients from `clients/` with each one's next action. A
 * sale moves a client from Prospects to Clients at once (I122 as changed; OQ91). The pill writes only `view`.
 */
export default function HomePage() {
  const [params, setParams] = useSearchParams();
  const meta = useMeta();
  const state = readHome(params);

  useEffect(() => {
    document.title = `${TITLES[state.view]} — 2Vantage`;
  }, [state.view]);

  const onView = (view) => setParams(viewParams(view), { replace: true });
  let body;
  if (state.view === 'book') {
    body = <ClientsView state={state} meta={meta} setParams={setParams} onView={onView} />;
  } else if (meta.isError) {
    body = <InlineError title="Could not load the lists." error={meta.error} onRetry={() => meta.refetch()} />;
  } else if (!meta.data) {
    body = <Loading />;
  } else {
    body = (
      <FeedView
        view={state.view}
        steps={state.steps}
        onSteps={(on) => setParams((current) => stepsParams(current, on), { replace: true })}
        meta={meta.data}
        onView={onView}
      />
    );
  }

  return (
    <div className="bb-dash">
      <div className="bnf-benefits-topbar">
        <div className="bb-eyebrow">Benefits</div>
      </div>
      {body}
    </div>
  );
}
