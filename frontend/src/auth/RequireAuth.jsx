import { Navigate, useLocation } from 'react-router';
import InlineError from '../ui/InlineError';
import Loading from '../ui/Loading';
import { useAuth } from './useAuth';

/** Signed-out visitors go to /login, then back to where they were going (plan.md §8.1). */
export default function RequireAuth({ children }) {
  const { user, status, error, retry, signedOutOnPurpose } = useAuth();
  const location = useLocation();

  if (status === 'loading') return <Loading label="Checking sign-in…" />;
  if (status === 'error') {
    return (
      <div className="page-container">
        <InlineError title="Could not reach 2Vantage." error={error} onRetry={() => retry()} />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace state={signedOutOnPurpose ? undefined : { from: location }} />;
  }
  return children;
}
