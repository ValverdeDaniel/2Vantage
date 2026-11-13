import { useState } from 'react';
import { useJourney } from '../../api/agenda';
import { LOST, useMeta } from '../../api/meta';
import { useOverview } from '../../api/overview';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import { ArchiveConfirm, ArchivedBanner, LostBanner, LostRow } from './Banners';
import CommissionCard from './CommissionCard';
import ConfidenceCard from './confidence/ConfidenceCard';
import CoverageNotesCard from './CoverageNotesCard';
import AskedList from './feed/AskedList';
import OutreachStrip from './feed/OutreachStrip';
import Timeline from './feed/Timeline';
import GetToMarketCard from './gtm/GetToMarketCard';
import MetricTiles from './MetricTiles';
import NotesCard from './notes/NotesCard';
import OverviewHeader from './OverviewHeader';
import QuoteToCloseCard from './QuoteToCloseCard';
import TitleActions from './TitleActions';
import WaitingBanner from './WaitingBanner';

/**
 * The deal's Overview tab (plan.md §8.6; Part M's O2, slice 62; old Vantage 891f1b3 `CaseOverviewTab.jsx`), the tab a
 * deal opens on. Its blocks keep the old order, except that the Waiting banner sits under the title, above the facts
 * (M33, X-84; OQ96's default): the title row with Mark as lost… and Archive…, their inline rows and banners, the
 * Waiting banner, the header with its client box and facts, the tiles, then Card 1 and Card 2 side by side, and under
 * them the Activity card (the outreach strip, "Who we've asked" and the Timeline) beside the side cards (Notes,
 * Coverage notes, Commission; slice 63; then Data confidence, slice 64). It reads `overview/`, the shell's `journey/`
 * (the banner, the Intake tile, Card 2's states), the deal header (lost, archived), the notes, the feed and review's
 * confidence; every control writes through the app that owns the value.
 */
export default function OverviewTab({ deal }) {
  const [open, setOpen] = useState(null); // the inline row showing: 'lost' | 'archive' | null
  const overview = useOverview(deal.id);
  const journey = useJourney(deal.id);
  const meta = useMeta();
  const lost = deal.stage === LOST;
  const close = () => setOpen(null);

  return (
    <div className="bb-tab-page">
      <TitleActions deal={deal} open={open} onOpen={setOpen} />
      {open === 'lost' && !lost && <LostRow deal={deal} onDone={close} />}
      {open === 'archive' && !deal.archived && <ArchiveConfirm deal={deal} onDone={close} />}
      {deal.archived && <ArchivedBanner deal={deal} />}
      {lost && <LostBanner deal={deal} />}
      {!lost && <WaitingBanner journey={journey.data} />}
      {overview.isError && (
        <InlineError
          title="Could not load the Overview."
          error={overview.error}
          onRetry={() => overview.refetch()}
          retrying={overview.isFetching}
        />
      )}
      {overview.isPending && <Loading label="Loading the Overview…" />}
      {overview.data && (
        <>
          <OverviewHeader deal={deal} overview={overview.data} meta={meta.data} />
          <MetricTiles tiles={overview.data.tiles} journey={journey.data} />
          <div className="bnf-phase-cols">
            <GetToMarketCard deal={deal} card={overview.data.get_to_market} meta={meta.data} />
            <QuoteToCloseCard deal={deal} rows={overview.data.quote_to_close} journey={journey.data} />
          </div>
          <div className="bb-overview-cols bnf-ov-cols">
            <div className="bb-panel-wide">
              <Timeline dealId={deal.id}>
                <OutreachStrip outreach={overview.data.outreach} />
                <AskedList outreach={overview.data.outreach} />
              </Timeline>
            </div>
            <div className="bb-overview-side">
              <NotesCard dealId={deal.id} />
              <CoverageNotesCard dealId={deal.id} notes={overview.data.coverage_notes} />
              <CommissionCard dealId={deal.id} commission={overview.data.commission} meta={meta.data} />
              <ConfidenceCard dealId={deal.id} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
