import { useState } from 'react';
import { useJourney } from '../../../api/agenda';
import { clientFeedKey, useClientWrites } from '../../../api/clientPage';
import { AskedList, CommissionCard, OutreachStrip, Timeline, WaitingBanner } from '../../../deal/overview';
import { errorText } from '../../../lib/errors';
import { clientPath } from '../clientTabs';
import { ArchiveConfirm, ArchivedBanner } from './ArchiveRows';
import ClientHeaderCard from './ClientHeaderCard';
import ClientTiles from './ClientTiles';
import ClientTitleRow from './ClientTitleRow';
import CoverageInForce from './CoverageInForce';
import DealCard from './DealCard';
import HistoryCard from './HistoryCard';
import LatestNotes from './LatestNotes';

const FEED_SUB = {
  current: "Every touch on the deal in flight, and the client's status changes.",
  none: "Every touch on this client's deals, and its status changes.",
};

// "Nothing due" when no deal is in flight: the old banner's Status words, without the renewal calendar (CL27).
function NothingInFlight() {
  return (
    <div className="bnf-next-banner bnf-next-done" role="status">
      <div className="bnf-next-label">Status</div>
      <div className="bnf-next-text">Nothing due — no deal in flight.</div>
    </div>
  );
}

/**
 * The client's Overview (plan.md §8.5; CL15–CL22; old Vantage 891f1b3 `ClientOverviewTab.jsx`), in the old order:
 * the title row (Convert to client in Start renewal's place, Archive client… with its confirm and banner), the header
 * card, the Waiting banner of the deal in flight, the tiles, the Deal card (the old Renewal card's look), Coverage in
 * force, then the Activity card over the client's deals (with the deal in flight's outreach strip and "Who we've
 * asked", as the old card had) beside the side cards — commission, Latest notes and History
 * with its chips (G116). The old upkeep card, Received figures and "Show me how ▸" wait or are dropped (CL27; OQ6).
 * It reads the page's two reads and the deal's `journey/`; every control writes through its owner's door.
 */
export default function ClientOverviewTab({ client, overview, meta }) {
  const [archiving, setArchiving] = useState(false);
  const dealId = overview.deal_id;
  const current = overview.current;
  const journey = useJourney(current?.deal_id);
  const writes = useClientWrites(client.id, dealId);
  const refused = writes.setStatus.isError ? errorText(writes.setStatus.error) : '';

  return (
    <div className="bb-tab-page">
      <ClientTitleRow
        client={client}
        overview={overview}
        writes={writes}
        archiving={archiving}
        onArchive={() => setArchiving(true)}
      />
      {refused && (
        <div role="alert" className="error-message">
          {refused}
        </div>
      )}
      {archiving && !client.archived && (
        <ArchiveConfirm writes={writes} onDone={() => setArchiving(false)} />
      )}
      {client.archived && <ArchivedBanner client={client} writes={writes} />}
      <ClientHeaderCard client={client} overview={overview} meta={meta} writes={writes} journey={journey.data} />
      <div className="bnf-cw-banner">
        {current ? <WaitingBanner journey={journey.data} /> : <NothingInFlight />}
      </div>
      <ClientTiles tiles={overview.tiles} />
      <div className="bnf-phase-cols">
        <DealCard overview={overview} journey={journey.data} meta={meta} />
      </div>
      <CoverageInForce block={overview.in_force} meta={meta} />
      <div className="bb-overview-cols bnf-ov-cols">
        <div className="bb-panel-wide">
          <Timeline
            path={`clients/${client.id}/activity/`}
            queryKey={clientFeedKey(client.id)}
            title="Activity"
            sub={current ? FEED_SUB.current : FEED_SUB.none}
            emptyText="Nothing recorded yet."
          >
            {overview.outreach && (
              <>
                <OutreachStrip outreach={overview.outreach} />
                <AskedList outreach={overview.outreach} />
              </>
            )}
          </Timeline>
        </div>
        <div className="bb-overview-side">
          {overview.commission && dealId && (
            <CommissionCard
              dealId={dealId}
              commission={overview.commission}
              meta={meta}
              to={clientPath(client.id, 'commissions')}
              linkLabel="Open Commissions tab →"
            />
          )}
          <LatestNotes clientId={client.id} dealId={dealId} inFlight={Boolean(current)} />
          <HistoryCard history={overview.history} meta={meta} />
        </div>
      </div>
    </div>
  );
}
