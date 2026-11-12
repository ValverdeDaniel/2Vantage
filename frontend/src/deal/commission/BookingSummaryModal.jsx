import { Link } from 'react-router';
import { useBookDeal, useDealCommission } from '../../api/commission';
import { useMeta } from '../../api/meta';
import { useAuth } from '../../auth/useAuth';
import { errorText } from '../../lib/errors';
import { formatMoney } from '../../lib/format';
import Modal from '../../ui/Modal';
import Tile from '../../ui/Tile';
import { useToast } from '../../ui/useToast';
import BookingRows from './BookingRows';

/*
 * The moment of truth after Mark sold (plan.md §8.13; H35; 891f1b3 `commissions/BookingSummaryModal.jsx`, its words
 * and classes): what got booked, line by line, with the holes booking could not fill, and who gets what. It opens when
 * the deal first becomes Sold, and again from any "Booked · view". The all tier fills holes here; the own tier sees it
 * read-only with its own share only; the none tier never sees it (the deal page does not open it for them). The
 * figures are the Commission tab's `booking` block; the browser does no money math.
 */
const NOT_VISIBLE = 'Booked — the commission ledger is visible to back office and the producers on the deal.';

export default function BookingSummaryModal({ dealId, onClose }) {
  const meta = useMeta().data;
  const { user } = useAuth();
  const canEdit = user.commissions_access === 'all';
  const query = useDealCommission(dealId);
  const booking = query.data?.booking;
  const holes = booking?.totals?.holes || 0;

  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      className="bnf-com-booking"
      title={`Booked — ${query.data?.client_name || 'this deal'}`}
      sub="What the ledger now expects for this deal, and who gets what. Premium, rate and splits are frozen from here; fill any holes now or later from Commissions."
      footer={
        <>
          <Link className="btn btn-secondary btn-sm" to={`/commissions?deal=${dealId}`} onClick={onClose}>
            Open in Commissions
          </Link>
          <button type="button" className="btn btn-primary btn-sm" onClick={onClose}>
            {holes && !canEdit ? 'Fix later' : 'Done'}
          </button>
        </>
      }
    >
      <div data-guide="booking-modal">
        {(query.isPending || !meta) && <div className="loading">Loading…</div>}
        {query.isError && <div className="bnf-com-placeholder">Could not load the booked records.</div>}
        {booking && meta && <Body dealId={dealId} booking={booking} canEdit={canEdit} meta={meta} />}
      </div>
    </Modal>
  );
}

function Body({ dealId, booking, canEdit, meta }) {
  if (!booking.sees_ledger) return <div className="bnf-com-placeholder">{NOT_VISIBLE}</div>;
  if (booking.state === 'unbooked') return <NotBooked dealId={dealId} canBook={booking.can_book} meta={meta} />;
  const records = booking.records || [];
  if (!records.length) {
    return <div className="bnf-com-empty">Nothing was booked — the deal has no sold plan on a line you are on.</div>;
  }
  const totals = booking.totals;
  return (
    <>
      <div className="bnf-com-tiles" style={{ marginBottom: 12 }}>
        <Tile
          label="Expected (annual)"
          value={totals.expected != null ? formatMoney(totals.expected) : '—'}
          tone="bb-green"
        />
        {canEdit && <Tile label="House share" value={totals.house != null ? formatMoney(totals.house) : '—'} />}
        <Tile label="Lines booked" value={records.length} />
        <Tile label="Holes" value={totals.holes} tone={totals.holes ? 'bb-amber' : 'bb-green'} />
      </div>
      <BookingRows records={records} canEdit={canEdit} meta={meta} />
      <div className="bnf-com-section-title" style={{ marginTop: 14 }}>
        Who gets what
      </div>
      <div className="bnf-com-people" data-guide="booking-people">
        {booking.people.map((person) => (
          <div key={`${person.role}:${person.name}`} className="bnf-com-booked-line">
            <span>
              <span className={`bnf-com-kind bnf-com-role-${person.role}`}>{person.role_label}</span>{' '}
              {person.role === 'house' ? '' : person.name}
            </span>
            <span>
              {person.pct_label}
              {person.amount != null ? <strong> · {formatMoney(person.amount)}</strong> : ''}
            </span>
          </div>
        ))}
      </div>
    </>
  );
}

function NotBooked({ dealId, canBook, meta }) {
  const toast = useToast();
  const book = useBookDeal(dealId);
  return (
    <div className="bnf-com-placeholder">
      {meta.commission?.not_booked || 'Sold — not booked'}: the sale is saved, but its commission did not book.
      {canBook && (
        <button
          type="button"
          className="btn btn-primary btn-sm"
          style={{ marginLeft: 10 }}
          disabled={book.isPending}
          onClick={() => book.mutate(undefined, { onError: (error) => toast.error(errorText(error)) })}
        >
          Book now
        </button>
      )}
    </div>
  );
}
