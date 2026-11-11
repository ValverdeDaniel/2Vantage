import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router';
import RequireAuth from './auth/RequireAuth';
import AppLayout from './pages/Layout/AppLayout';
import ErrorBoundary from './ui/ErrorBoundary';
import { PageSpinner } from './ui/Spinner';

// Every page is its own bundle (plan.md §3.9).
const LoginPage = lazy(() => import('./auth/LoginPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage/DashboardPage'));
const DealPage = lazy(() => import('./pages/DealPage/DealPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage/NotFoundPage'));

// Routes (plan.md §8.1, Release 1). /deals/:dealId opens the first tab; DealPage sends unknown tabs there too.
export default function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageSpinner />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <RequireAuth>
                <AppLayout />
              </RequireAuth>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="deals/:dealId" element={<Navigate to="advisor" replace />} />
            <Route path="deals/:dealId/:tab" element={<DealPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}
