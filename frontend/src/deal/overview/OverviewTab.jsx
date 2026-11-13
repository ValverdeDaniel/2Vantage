import { useState } from 'react';
import { useJourney } from '../../api/agenda';
import { LOST, useMeta } from '../../api/meta';
import { useOverview } from '../../api/overview';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import { ArchiveConfirm, ArchivedBanner, LostBanner, LostRow } from './Banners';
import MetricTiles from './MetricTiles';
import OverviewHeader from './OverviewHeader';
import TitleActions from './TitleActions';
import WaitingBanner from './WaitingBanner';

/**
 * The deal's Overview tab (plan.md §8.6; Part M's O2, slice 62; old Vantage 891f1b3 `CaseOverviewTab.jsx`), the tab a
 * deal opens on. Its blocks keep the old order, except that the Waiting banner sits under the title, above the facts
 * (M33, X-84; OQ96's default): the title row with Mark as lost… and Archive…, their inline rows and banners, the
 * Waiting banner, the header with its client box and facts, then the tiles. Card 1, Card 2, the feed, notes and side
 * cards follow in slice 63, data confidence in 64. It reads `overview/`, the shell's `journey/` (the banner, the
 * Intake tile) and the deal header (lost, archived); every control writes through the app that owns the value.
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
        </>
      )}
    </div>
  );
}
