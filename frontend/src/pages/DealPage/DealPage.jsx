import { lazy, Suspense, useEffect } from 'react';
import { Link, Navigate, useParams } from 'react-router';
import { useDeal } from '../../api/deals';
import { useMeta } from '../../api/meta';
import { errorStatus } from '../../lib/errors';
import Button from '../../ui/Button';
import EmptyState from '../../ui/EmptyState';
import ErrorBoundary from '../../ui/ErrorBoundary';
import InlineError from '../../ui/InlineError';
import Skeleton from '../../ui/Skeleton';
import Tabs from '../../ui/Tabs';
import DealHeader from './DealHeader';
import styles from './DealPage.module.css';

// Release 1 tabs (plan.md §8.4). Each is its own bundle and receives the deal header as `deal`.
const TABS = [
  { key: 'advisor', label: 'Advisor', Component: lazy(() => import('../../deal/advisor/AdvisorTab')) },
  { key: 'proposal', label: 'Proposal', Component: lazy(() => import('../../deal/proposal/ProposalTab')) },
  { key: 'documents', label: 'Documents', Component: lazy(() => import('../../deal/documents/DocumentsTab')) },
];
const FIRST_TAB = TABS[0].key;

function DealSkeleton() {
  return (
    <div className={styles.page}>
      <Skeleton lines={3} height="22px" width="40%" label="Loading the deal…" />
      <div className={styles.body}>
        <Skeleton lines={3} height="28px" width="100%" label="" />
        <Skeleton lines={6} height="18px" label="" />
      </div>
    </div>
  );
}

/** One deal: the header stays mounted while tabs switch (the header query never reloads on a tab change). */
export default function DealPage() {
  const { dealId, tab } = useParams();
  const validId = /^\d+$/.test(dealId || '');
  const header = useDeal(validId ? dealId : null);
  const meta = useMeta();
  const clientName = header.data?.client.name;

  useEffect(() => {
    if (clientName) document.title = `${clientName} — 2Vantage`;
  }, [clientName]);

  const current = TABS.find((item) => item.key === tab);
  if (validId && !current) return <Navigate to={`/deals/${dealId}/${FIRST_TAB}`} replace />;

  if (!validId || (header.isError && errorStatus(header.error) === 404)) {
    return (
      <EmptyState
        title="This deal does not exist."
        action={
          <Button as={Link} to="/" variant="primary">
            Back to clients
          </Button>
        }
      >
        It may have been deleted, or the link may be wrong.
      </EmptyState>
    );
  }
  if (header.isError || meta.isError) {
    const failed = header.isError ? header : meta;
    return (
      <InlineError
        title="Could not load this deal."
        error={failed.error}
        onRetry={() => failed.refetch()}
        retrying={failed.isFetching}
      />
    );
  }
  if (header.isPending || meta.isPending) return <DealSkeleton />;

  const deal = header.data;
  const Tab = current.Component;
  return (
    <div className={styles.page}>
      <DealHeader key={deal.id} deal={deal} meta={meta.data} />
      <div className={styles.body}>
        <Tabs
          label="Deal sections"
          orientation="vertical"
          className={styles.tabs}
          items={TABS.map((item) => ({ to: `/deals/${deal.id}/${item.key}`, label: item.label }))}
        />
        <section className={styles.panel} aria-label={current.label}>
          <ErrorBoundary resetKey={current.key}>
            <Suspense fallback={<Skeleton lines={6} height="18px" label={`Loading ${current.label}…`} />}>
              <Tab deal={deal} />
            </Suspense>
          </ErrorBoundary>
        </section>
      </div>
    </div>
  );
}
