import { lazy, Suspense, useEffect, useSyncExternalStore } from 'react';
import { useSearchParams } from 'react-router';
import { useAuth } from '../../auth/useAuth';
import * as bookingBridge from '../../deal/shared/bookingBridge';

// Loaded only when it opens: the commission folder's bundle stays off the deal page until then.
const BookingSummaryModal = lazy(() =>
  import('../../deal/commission').then((module) => ({ default: module.BookingSummaryModal })),
);

/*
 * The deal page's one booking summary (plan.md §8.13; H35): shown while `deal/shared/bookingBridge` names this deal —
 * the board opens it when a Mark sold first makes the deal Sold, and "Booked · view" (or `?booking=1`, the old link)
 * opens it again. Never for a user with no commission tier (the old ComparisonGrid's `canSeeCommissions`).
 */
export default function BookingSlot({ deal }) {
  const { user } = useAuth();
  const openFor = useSyncExternalStore(bookingBridge.subscribe, bookingBridge.current);
  const [params, setParams] = useSearchParams();
  const asked = params.get('booking') === '1';

  useEffect(() => {
    if (!asked) return;
    bookingBridge.open(deal.id);
    const next = new URLSearchParams(params);
    next.delete('booking');
    setParams(next, { replace: true });
  }, [asked, deal.id, params, setParams]);

  useEffect(() => () => bookingBridge.close(), [deal.id]);

  if (openFor !== deal.id || user.commissions_access === 'none') return null;
  return (
    <Suspense fallback={null}>
      <BookingSummaryModal dealId={deal.id} onClose={bookingBridge.close} />
    </Suspense>
  );
}
