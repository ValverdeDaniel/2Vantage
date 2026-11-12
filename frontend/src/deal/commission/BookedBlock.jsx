import { Link } from 'react-router';
import { BOOK_EXPORT_PATH, disclosurePath, useBookDeal } from '../../api/commission';
import { downloadFile } from '../../lib/download';
import { errorText } from '../../lib/errors';
import { formatMoney } from '../../lib/format';
import ExportButton from '../../ui/ExportButton';
import { useToast } from '../../ui/useToast';
import * as bookingBridge from '../shared/bookingBridge';

/*
 * What the sale booked, under the rates grid (plan.md §8.13; H23, H25, H35, H108, H120; 891f1b3
 * `overview/CommissionPanel.jsx`'s booked block, its words and classes): the booked total, the house and the pool
 * (all tier), the lines with holes ("fix ↗"), each out-of-date record with its one-click Update, and the foot with
 * "Booked · view", "Comp disclosure ⤓" (all tier) and Export. A sale that did not book reads "Sold — not booked ·
 * Book now". Every figure is the server's `booking` block.
 */
export default function BookedBlock({ dealId, booking, meta }) {
  const toast = useToast();
  const book = useBookDeal(dealId);
  const words = meta.commission || {};
  const rebook = (done) =>
    book.mutate(undefined, {
      onSuccess: () => toast.success(done),
      onError: (error) => toast.error(errorText(error)),
    });

  if (booking.state === 'none') return null;
  if (booking.state === 'unbooked') {
    return (
      <div className="bnf-com-booked" data-guide="overview-booked">
        <div className="bnf-com-booked-line bnf-com-holes-line">
          <span className="bb-amber">{words.not_booked || 'Sold — not booked'}</span>
          {booking.can_book && (
            <button type="button" className="btn btn-primary btn-sm" disabled={book.isPending} onClick={() => rebook('Booked')}>
              Book now
            </button>
          )}
        </div>
      </div>
    );
  }
  const totals = booking.totals || {};
  const lines = booking.record_count;
  return (
    <div className="bnf-com-booked" data-guide="overview-booked">
      <div className="bnf-com-booked-line">
        <span>
          Booked at sale ({lines} line{lines === 1 ? '' : 's'})
        </span>
        <span className={totals.expected != null ? 'bb-green' : 'bb-empty'}>
          {totals.expected != null ? formatMoney(totals.expected) : '—'}
        </span>
      </div>
      {booking.sees_ledger && 'house' in totals && (
        <>
          <div className="bnf-com-booked-line">
            <span>House share</span>
            <span>{totals.house != null ? formatMoney(totals.house) : '—'}</span>
          </div>
          <div className="bnf-com-booked-line">
            <span>Producer pool</span>
            <span>{totals.pool != null ? formatMoney(totals.pool) : '—'}</span>
          </div>
        </>
      )}
      {totals.holes > 0 && (
        <div className="bnf-com-booked-line bnf-com-holes-line">
          <span className="bb-amber">
            {totals.holes} line{totals.holes === 1 ? '' : 's'} with holes (premium or rate not known)
          </span>
          <Link to={`/commissions?deal=${dealId}`}>fix ↗</Link>
        </div>
      )}
      {(booking.stale || []).map((stale) => (
        <div key={stale.record_id} className="bnf-com-booked-line bnf-com-holes-line" data-guide="booking-stale">
          <span className="bb-amber">
            Out of date: {formatMoney(stale.before, { empty: '—' })} → {formatMoney(stale.after, { empty: '—' })}
            <span className="bb-drop-meta"> · {stale.carrier || stale.line}</span>
          </span>
          <button type="button" className="btn btn-secondary btn-sm" disabled={book.isPending} onClick={() => rebook('Rebooked')}>
            Update
          </button>
        </div>
      ))}
      {booking.sees_ledger && (
        <div className="bb-drop-meta bnf-com-booked-foot" style={{ marginTop: 6 }}>
          <span>
            Frozen when the deal sold — premium, rate and splits.{' '}
            <button type="button" className="bnf-linklike" onClick={() => bookingBridge.open(dealId)}>
              Booked · view
            </button>{' '}
            · <Link to={`/commissions?deal=${dealId}`}>Open in Commissions</Link>
            {booking.disclosure && (
              <>
                {' · '}
                <button
                  type="button"
                  className="bnf-linklike"
                  title={words.disclosure_hint}
                  onClick={() =>
                    downloadFile(disclosurePath(dealId), { fallbackName: 'comp-disclosure.pdf' }).catch((error) =>
                      toast.error(errorText(error)),
                    )
                  }
                >
                  Comp disclosure ⤓
                </button>
              </>
            )}
          </span>
          <ExportButton
            path={BOOK_EXPORT_PATH}
            params={{ deal: dealId }}
            fallbackName="commission-book.xlsx"
            title="Download this deal's booked lines as an Excel workbook"
          />
        </div>
      )}
    </div>
  );
}
