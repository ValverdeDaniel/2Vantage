import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router';
import RequireAuth from './auth/RequireAuth';
import AppShell from './pages/Layout/AppShell';
import ErrorBoundary from './ui/ErrorBoundary';
import Loading from './ui/Loading';

// Every page is its own bundle (plan.md §3.9).
const LoginPage = lazy(() => import('./auth/LoginPage'));
const HomePage = lazy(() => import('./pages/HomePage/HomePage'));
const ArchivedPage = lazy(() => import('./pages/ArchivedPage/ArchivedPage'));
const NewDealPage = lazy(() => import('./pages/NewDealPage/NewDealPage')); // A14, D43 (slice 20)
const DealRedirect = lazy(() => import('./pages/DealPage/DealRedirect'));
const DealPage = lazy(() => import('./pages/DealPage/DealPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage/NotFoundPage'));
// A deal's file in its own window, with no top bar (E69–E71; slice 65): the Documents tab's bundle.
const DocumentWindowPage = lazy(() => import('./deal/documents').then((m) => ({ default: m.DocumentWindowPage })));

// Routes (plan.md §8.1). The deal's tab is in the path; /deals/:dealId (and an old ?tab= link) opens a tab there.
export default function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/deals/:dealId/documents/:docId/window"
            element={
              <RequireAuth>
                <DocumentWindowPage />
              </RequireAuth>
            }
          />
          <Route
            element={
              <RequireAuth>
                <AppShell />
              </RequireAuth>
            }
          >
            <Route index element={<HomePage />} />
            <Route path="archived" element={<ArchivedPage />} />
            <Route path="deals/new" element={<NewDealPage />} />
            <Route path="deals/:dealId" element={<DealRedirect />} />
            <Route path="deals/:dealId/:tab" element={<DealPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}
