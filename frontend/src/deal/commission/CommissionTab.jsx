import { useDealCommission } from '../../api/commission';
import { useMeta } from '../../api/meta';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import RefreshChip from '../../ui/RefreshChip';
import BookedBlock from './BookedBlock';
import FrozenSplits from './FrozenSplits';
import RatesGrid from './RatesGrid';
import SplitEditor from './SplitEditor';

/*
 * The deal's Commission tab (plan.md §8.13; H1–H24; 891f1b3 `shared/CommissionTab.jsx`, its words and classes): what
 * we agreed with the carrier and what it is worth (the rates grid), who gets what (the split editor) and "How this
 * books". Open to every deal user (H102). After the sale (slice 49): the booked block under the grid (H23, H25, H35,
 * H108, H120) and, in place of the editor, the shares as booked; the nudge then asks to set the primary and Rebook.
 */
export default function CommissionTab({ deal }) {
  const meta = useMeta().data;
  const query = useDealCommission(deal.id);
  const payload = query.data;

  if (query.isPending || !meta) return <Loading label="Loading..." />;
  if (query.isError) return <InlineError title="Commission" error={query.error} onRetry={() => query.refetch()} />;
  const booking = payload.booking;
  const booked = booking.state === 'booked';

  return (
    <div className="bb-tab-page">
      <div className="bnf-ov-titlerow">
        <div>
          <div className="bb-tab-title">
            Commission
            <RefreshChip
              loading={query.isFetching && !query.isPending}
              error={query.isRefetchError}
              onRetry={() => query.refetch()}
            />
          </div>
          <div className="bb-subtitle">
            What we agreed with the carrier, who gets what among our producers and referral agents, and what the sale
            froze.
          </div>
        </div>
      </div>

      {payload.split.needs_primary && !booked && (
        <div className="bnf-com-nudge bnf-com-nudge-wide" data-guide="commission-nudge">
          <strong>No primary producer set.</strong> Pick who is on the AOR letter under Producers &amp; splits so the
          split is known before the first check — until then the house is shown keeping 100&nbsp;%.
        </div>
      )}
      {payload.split.needs_primary && booked && (
        <div className="bnf-com-nudge bnf-com-nudge-wide" data-guide="commission-nudge">
          <strong>Booked with the house at 100&nbsp;%.</strong> Set the primary producer, then Rebook from Commissions.
        </div>
      )}

      <div className="bnf-com-tabgrid">
        <div className="bnf-com-tabgrid-main">
          <RatesGrid dealId={deal.id} payload={payload} meta={meta} />
          <BookedBlock dealId={deal.id} booking={booking} meta={meta} />
        </div>
        <div className="bnf-com-tabgrid-side">
          {booked && booking.frozen?.length ? (
            <FrozenSplits dealId={deal.id} frozen={booking.frozen} />
          ) : (
            <SplitEditor
              dealId={deal.id}
              split={payload.split}
              basis={payload.basis}
              preview={payload.preview}
              meta={meta}
            />
          )}
          <HowThisBooks />
        </div>
      </div>
    </div>
  );
}

function HowThisBooks() {
  return (
    <div className="bb-panel bnf-com-howbooks">
      <div className="bb-panel-title">How this books</div>
      <ol className="bnf-com-howlist">
        <li>Expected revenue per line = premium × the agreed rate (or the flat $, or PEPM × enrolled × 12).</li>
        <li>
          The house takes its share first — from the primary producer’s year-1 / renewal share (or the firm default).
        </li>
        <li>
          Fixed $ / PEPM rows come off the producer pool, then % rows are a % of what is left; the primary keeps the
          rest.
        </li>
        <li>
          <em>Mark as sold</em> freezes all of it — premium, rate and every share — as records in Commissions. Later
          edits are explicit and logged.
        </li>
      </ol>
    </div>
  );
}
