import { useIntake } from '../../api/intake';
import { useMeta } from '../../api/meta';
import { useRfp } from '../../api/rfp';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import RefreshChip from '../../ui/RefreshChip';
import { ChecklistCard, CoverageIntentCard } from '../intake';
import BuilderCard from '../shared/BuilderCard';
import CompletedMark from '../shared/CompletedMark';
import CensusLine from './CensusLine';
import RequestCard from './RequestCard';
import { requestSummary } from './requestModel';
import useRfpCards from './useRfpCards';
import useRfpWrites from './useRfpWrites';

/*
 * The RFP tab (plan.md §8.12; K1–K33; old CarriersTab.jsx at 891f1b3, `bb-tab-page`, same classes and words): the
 * title and subtitle with the legal name (K4), "✓ N of M completed" and Collapse all (K6, K7), the census line (K8),
 * then the cards in working order, each collapsible and marked completed (K9): 1 What we're shopping, intake's
 * Coverage & marketing intent card with its own Confirmed beside this page's mark (K12–K16; OQ60: both); 2 What we're
 * requesting (K17–K29); 3 intake's Marketing readiness checklist (K31, K32). The packet and the emails join with
 * slices 45 and 46, and with the Emails card the Mark as marketed footer (K33). "Show me how ▸" is dropped (K5).
 */
export default function RfpTab({ deal }) {
  const meta = useMeta().data;
  const rfp = useRfp(deal.id);
  const intake = useIntake(deal.id);
  const rfpMeta = meta?.rfp;
  const writes = useRfpWrites(deal.id, (rfpMeta?.funding || []).map((entry) => entry.key));
  const page = rfp.data;
  const cards = useRfpCards({
    cards: rfpMeta?.cards,
    available: { coverage: Boolean(intake.data), request: Boolean(page), checklist: Boolean(intake.data?.checklist) },
    done: page?.done,
    writes,
    checklist: intake.data?.checklist,
  });

  if (rfp.isPending || !rfpMeta) return <Loading label="Loading..." />;
  if (rfp.isError) return <InlineError title="RFP" error={rfp.error} onRetry={() => rfp.refetch()} />;

  const mark = (key) => {
    const card = cards.card(key);
    return <CompletedMark done={card.done} busy={card.busy} onToggleDone={card.onToggleDone} />;
  };
  const panel = (key) => {
    const card = cards.card(key);
    return { open: card.open, onToggleOpen: () => card.onToggleOpen(), mark: mark(key) };
  };

  return (
    <div className="bb-tab-page">
      <div className="bb-tab-title">
        RFP
        <RefreshChip
          loading={rfp.isFetching && !rfp.isPending}
          error={rfp.isRefetchError}
          onRetry={() => rfp.refetch()}
        />
      </div>
      <div className="bb-subtitle">
        The request that goes out for {page.client_name}. Tick what belongs in the packet and download it as one zip.
        Checking the data happens on the Census tab.
      </div>

      <div className="bnf-build-toolbar bnf-rfp-toolbar">
        <span className={`bnf-build-progress${cards.progress.all ? ' bnf-build-progress-done' : ''}`}>
          ✓ {cards.progress.done} of {cards.progress.total} completed
        </span>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => cards.setAllOpen(!cards.allOpen)}>
          {cards.allOpen ? 'Collapse all' : 'Expand all'}
        </button>
      </div>

      <CensusLine dealId={deal.id} census={page.census} band={page.band} />

      {intake.data && (
        <div className="bb-mb" data-guide="rfp-coverage">
          <CoverageIntentCard deal={deal} meta={meta} intent={intake.data.intent} {...panel('coverage')} />
        </div>
      )}

      <BuilderCard
        title={rfpMeta.cards.find((entry) => entry.key === 'request')?.label}
        summary={requestSummary(page.request, rfpMeta.routes)}
        card={cards.card('request')}
        guide="carriers-request"
        className="bnf-rfp-card bnf-rfp-request bb-mb"
      >
        <RequestCard page={page} rfpMeta={rfpMeta} onSave={writes.save} />
      </BuilderCard>

      {intake.data?.checklist && (
        <div className="bb-mb" data-guide="rfp-checklist">
          <ChecklistCard
            deal={deal}
            meta={meta}
            checklist={intake.data.checklist}
            sentAt={intake.data.marketed?.at}
            {...panel('checklist')}
          />
        </div>
      )}
    </div>
  );
}
