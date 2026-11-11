import { Navigate, useLocation } from 'react-router';
import InlineError from '../ui/InlineError';
import { PageSpinner } from '../ui/Spinner';
import { useAuth } from './useAuth';

/** Signed-out visitors go to /login, then back to where they were going (plan.md §8.1). */
export default function RequireAuth({ children }) {
  const { user, status, error, retry, signedOutOnPurpose } = useAuth();
  const location = useLocation();

  if (status === 'loading') return <PageSpinner label="Checking sign-in…" />;
  if (status === 'error') {
    return <InlineError title="Could not reach 2Vantage." error={error} onRetry={() => retry()} />;
  }
  if (!user) {
    return <Navigate to="/login" replace state={signedOutOnPurpose ? undefined : { from: location }} />;
  }
  return children;
}
