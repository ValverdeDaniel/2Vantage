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
// Producers & partners and Settings (H95–H101; slice 48); the Book and By person join with slice 49.
const CommissionsPage = lazy(() => import('./pages/CommissionsPage/CommissionsPage'));
const NewDealPage = lazy(() => import('./pages/NewDealPage/NewDealPage')); // A14, D43 (slice 20)
const DealRedirect = lazy(() => import('./pages/DealPage/DealRedirect'));
const DealPage = lazy(() => import('./pages/DealPage/DealPage'));
const ClientPage = lazy(() => import('./pages/ClientPage/ClientPage')); // §8.5; slices 67–68
const NotFoundPage = lazy(() => import('./pages/NotFoundPage/NotFoundPage'));
// A deal's file in its own window, with no top bar (E69–E71; slice 65): the Documents tab's bundle.
const DocumentWindowPage = lazy(() => import('./deal/documents').then((m) => ({ default: m.DocumentWindowPage })));
// The client portal and its neighbours, outside the app shell (§8.20; L76, L78, L136; slice 54).
const PortalPage = lazy(() => import('./portal/PortalPage'));
const PreviewPage = lazy(() => import('./portal/PreviewPage'));
const MovedPage = lazy(() => import('./portal/MovedPage'));

// Routes (plan.md §8.1). The deal's tab is in the path; /deals/:dealId (and an old ?tab= link) opens a tab there.
export default function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/portal/:token" element={<PortalPage />} />
          <Route path="/b/:token" element={<MovedPage />} />
          <Route
            path="/preview/links/:linkId"
            element={
              <RequireAuth>
                <PreviewPage />
              </RequireAuth>
            }
          />
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
            <Route path="commissions" element={<CommissionsPage />} />
            <Route path="deals/new" element={<NewDealPage />} />
            <Route path="deals/:dealId" element={<DealRedirect />} />
            <Route path="deals/:dealId/:tab" element={<DealPage />} />
            {/* The client page: /clients/:id opens its Overview, as an unknown or unbuilt tab does. */}
            <Route path="clients/:clientId/:tab?" element={<ClientPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}
