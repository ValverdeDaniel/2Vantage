import { useCallback, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { useAiState } from '../../api/ai';
import { useMeta } from '../../api/meta';
import ErrorBoundary from '../../ui/ErrorBoundary';
import { useToast } from '../../ui/useToast';
import ClaudeStrip from './ClaudeStrip';
import DealDrawer from './DealDrawer';
import { claudeDoor, PILL_TABS, STRIP_TABS, useClaudeDoor } from './door';
import { modelLabel, nextModel, tabKinds } from './drawerWords';
import { afterTurn } from './afterTurn';
import { flashWhenSettled } from './flashPlans';

/*
 * Work with Claude around every deal tab (plan.md §8.4, §8.17; A25, D1, D3, D34, D35, D71; the old CaseWorkspace's
 * door, drawer and ClaudeStrip), mounted once in the deal shell so it survives moving between tabs:
 * - the strip over the tables Claude reads into (Intake, Census, Questionnaire, Advisor, Proposal);
 * - the navy ✦ Work with Claude pill, bottom-right on the tabs it works over, hidden while the drawer is open (D1);
 * - the drawer: the pill or a tab's door ("＋ Add quotes", a drop on Documents) opens it and it stays open across tabs;
 *   `?claude=1` opens it too, and one the URL opened closes when the parameter goes (D3);
 * - a finished read's plans flash on the table once it has refetched, automatic landings included (D35, F112).
 * Nothing shows without Claude set up (D26). Its own error boundary keeps a failure here from taking the tab down.
 */
export default function WorkWithClaude({ deal, tab }) {
  return (
    <ErrorBoundary resetKey={`${deal.id}:${tab}`} fallback={() => null}>
      <AroundTheTab deal={deal} tab={tab} />
    </ErrorBoundary>
  );
}

function AroundTheTab({ deal, tab }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { data: meta } = useMeta();
  const door = useClaudeDoor();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const asked = params.get('claude') === '1';
  const onFinished = useCallback(
    (job) => {
      if (job.kind === 'turn') {
        afterTurn(queryClient, deal.id, job, () => navigate(`/deals/${deal.id}/advisor${asked ? "?claude=1" : ""}`));
        return;
      }
      if (job.kind !== 'read') return;
      if (job.landed?.plan_ids?.length) flashWhenSettled(queryClient, deal.id, job.landed.plan_ids);
      else if (job.status === 'done' && job.land === 'staged' && job.wait_reason) {
        toast.info(`Claude read the files — ${job.wait_reason.charAt(0).toLowerCase()}${job.wait_reason.slice(1)}`);
      }
    },
    [deal.id, queryClient, toast, navigate, asked],
  );
  const ai = useAiState(deal.id, { onFinished });
  const state = ai.data;

  useEffect(() => claudeDoor.enter(deal.id), [deal.id]);
  useEffect(() => {
    if (asked) claudeDoor.open('', { byParam: true });
    else claudeDoor.closeIfByParam();
  }, [asked]);

  if (!meta?.ai || !state?.claude) return null;
  const kinds = tabKinds(meta, tab);
  const kind = kinds.includes(door.kind) ? door.kind : kinds[0] || '';
  const retryFor = (news) => {
    const next = nextModel(meta, news.model, state.can?.opus);
    return next ? { model: next, label: modelLabel(meta, next) } : null;
  };
  const close = () => {
    claudeDoor.close();
    if (params.has('claude')) {
      const next = new URLSearchParams(params);
      next.delete('claude');
      setParams(next, { replace: true });
    }
  };

  return (
    <>
      {STRIP_TABS.has(tab) && (
        <ClaudeStrip dealId={deal.id} state={state} dismissed={door.dismissed} retryFor={retryFor} />
      )}
      {PILL_TABS.has(tab) && !door.open && (
        <button
          type="button"
          className="btn btn-primary bnf-wwc-fab"
          aria-label="Work with Claude"
          title="Read what belongs on this tab — carrier quotes on the Advisor — in a panel over this page"
          onClick={() => claudeDoor.open(kind)}
        >
          <span className="bnf-wwc-fab-glyph" aria-hidden="true">
            ✦
          </span>
          <span className="bnf-wwc-fab-label">Work with Claude</span>
        </button>
      )}
      {door.open && (
        <DealDrawer
          deal={deal}
          tab={tab}
          meta={meta}
          state={state}
          door={door}
          kind={kind}
          kinds={kinds}
          retryFor={retryFor}
          onClose={close}
        />
      )}
    </>
  );
}
