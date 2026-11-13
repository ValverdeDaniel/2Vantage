import { Link } from 'react-router';
import { BOOK_EXPORT_PATH, useClientBook, useClientSplit } from '../../../api/commission';
import { useAuth } from '../../../auth/useAuth';
import { SplitEditor } from '../../../deal/commission';
import { formatMoney } from '../../../lib/format';
import ExportButton from '../../../ui/ExportButton';
import InlineError from '../../../ui/InlineError';
import Loading from '../../../ui/Loading';
import Tile from '../../../ui/Tile';
import BookedByYear from './BookedByYear';

function Tiles({ totals, isAll }) {
  const money = (value) => (value != null ? formatMoney(value) : '—');
  return (
    <div className="bb-metric-row bnf-com-tiles">
      <Tile
        label="Expected / yr"
        value={money(totals.expected)}
        tone="bb-green"
        title="Expected agency revenue across every booked year (status booked / active)"
      />
      {isAll && <Tile label="House share" value={money(totals.house)} />}
      {isAll && <Tile label="Producer pool" value={money(totals.pool)} />}
      <Tile
        label="Next 12 months"
        value={money(totals.next_12)}
        title="Expected income from records in force over the next twelve months"
      />
    </div>
  );
}

function HowThisClientBooks() {
  return (
    <div className="bb-panel">
      <div className="bb-panel-title">How this client books</div>
      <div className="bnf-com-howlist">
        <div>
          0 · The primary producer in <b>Who gets what on this client</b> is what the client&apos;s <b>Owner</b> projects
          — change it by changing the schedule, not the other way round. It applies to every deal on this client unless a
          deal overrides it.
        </div>
        <div>1 · Each year&apos;s deal carries the agreed carrier rate per line (its Commission tab) and inherits these people.</div>
        <div>2 · Mark as sold freezes one record per line — premium, rate, plan, and every split as a % of agency revenue.</div>
      </div>
    </div>
  );
}

function Ledger({ book, meta, tier }) {
  if (tier === 'none') {
    return (
      <div className="bb-panel">
        <div className="bb-panel-title">Booked, by plan year</div>
        <div className="bb-drop-meta">
          The ledger is hidden for this login (commissions access: none). Who gets what on this client can still be
          set below.
        </div>
      </div>
    );
  }
  if (book.isPending) return <Loading label="Loading the booked records…" />;
  if (book.isError) {
    return <InlineError title="Could not load the booked records." error={book.error} onRetry={() => book.refetch()} />;
  }
  const data = book.data;
  return (
    <>
      {data.tier === 'own' && (
        <div className="bnf-next-banner bnf-next-info">
          <div>
            <div className="bnf-next-label">Your share</div>
            <div className="bnf-next-text">
              Showing only the records you hold a share of — the totals below are your slice of this client, not the
              whole statement.
            </div>
          </div>
        </div>
      )}
      <Tiles totals={data.totals} isAll={data.tier === 'all'} />
      <BookedByYear book={data} meta={meta} />
    </>
  );
}

/**
 * The client's Commissions (plan.md §8.5; CL25, H106; old Vantage 891f1b3 `radar/client/ClientCommissionsTab.jsx`):
 * the title with Export and "Open in Commissions ↗" (the Book on this client, once anything is booked); the own tier's
 * "Your share" banner; the
 * tiles and "Booked, by plan year", both in the viewer's tier (`clients/{id}/commission/records/`; hidden for the none
 * tier); then "Who gets what on this client" — the client-scope split editor (H106), which every user reads and the
 * all tier or the client's owner saves (OQ70) — beside "How this client books". The client statement, its export,
 * Received and gaps wait for the ledger (H103, H105; OQ6); Start renewal and comp agreements wait (CL27, H107).
 */
export default function ClientCommissionsTab({ client, meta }) {
  const { user } = useAuth();
  const tier = user.commissions_access;
  const split = useClientSplit(client.id);
  const book = useClientBook(client.id, { enabled: tier !== 'none' });
  const booked = book.data?.rows?.length > 0;
  return (
    <div className="bb-tab-page">
      <div className="bnf-ov-titlerow">
        <div>
          <div className="bb-tab-title">Commissions</div>
          <div className="bb-subtitle">What this client pays, who gets what, year by year.</div>
        </div>
        {booked && (
          <div className="bnf-cw-titlebtns">
            <ExportButton
              path={BOOK_EXPORT_PATH}
              params={{ client: client.id }}
              fallbackName="commission-book.xlsx"
              title="Download this client's booked records as an Excel workbook"
            />
            <Link className="btn btn-secondary btn-sm" to={`/commissions?client=${client.id}`}>
              Open in Commissions ↗
            </Link>
          </div>
        )}
      </div>

      <Ledger book={book} meta={meta} tier={tier} />

      <div className="bnf-cw-com-below">
        <div>
          {split.isPending && <Loading label="Loading the split…" />}
          {split.isError && (
            <InlineError title="Could not load the split." error={split.error} onRetry={() => split.refetch()} />
          )}
          {split.data && (
            <SplitEditor
              clientId={client.id}
              split={split.data.split}
              basis={split.data.basis}
              preview={split.data.preview}
              meta={meta}
              title="Who gets what on this client"
            />
          )}
        </div>
        <HowThisClientBooks />
      </div>
    </div>
  );
}
