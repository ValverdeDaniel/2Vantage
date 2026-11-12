import { Suspense } from 'react';
import { Outlet, useLocation } from 'react-router';
import ErrorBoundary from '../../ui/ErrorBoundary';
import Loading from '../../ui/Loading';
import TopBar from './TopBar';

/**
 * AppShell (A6, O.4): the old fixed navy top bar, then the signed-in page in the old `page-container`. Pages load
 * inside it, so the bar never flashes while a page bundle loads.
 */
export default function AppShell() {
  const { pathname } = useLocation();
  // A crashed page clears when another page opens; a deal's tabs keep their own boundary (DealPage).
  const page = pathname.split('/').slice(0, 3).join('/');
  return (
    <>
      <TopBar />
      <main className="page-container">
        <ErrorBoundary resetKey={page}>
          <Suspense fallback={<Loading />}>
            <Outlet />
          </Suspense>
        </ErrorBoundary>
      </main>
    </>
  );
}
