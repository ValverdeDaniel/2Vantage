import { Suspense } from 'react';
import { Outlet, useLocation } from 'react-router';
import ErrorBoundary from '../../ui/ErrorBoundary';
import { PageSpinner } from '../../ui/Spinner';
import styles from './AppLayout.module.css';
import TopBar from './TopBar';

/** Top bar + the signed-in page. Pages load inside, so the bar never flashes while a page bundle loads. */
export default function AppLayout() {
  const { pathname } = useLocation();
  // Reset a crashed page when another page opens; tabs of one deal keep their own boundary.
  const page = pathname.split('/').slice(0, 3).join('/');
  return (
    <div className={styles.shell}>
      <a className={styles.skip} href="#main">
        Skip to content
      </a>
      <TopBar />
      <main id="main" className={styles.main} tabIndex={-1}>
        <ErrorBoundary resetKey={page}>
          <Suspense fallback={<PageSpinner />}>
            <Outlet />
          </Suspense>
        </ErrorBoundary>
      </main>
    </div>
  );
}
