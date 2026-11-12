import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Navigate, useLocation, useSearchParams } from 'react-router';
import { getSignInOptions } from '../api/accounts';
import { errorText } from '../lib/errors';
import Loading from '../ui/Loading';
import MicrosoftSignIn from './MicrosoftSignIn';
import { useAuth } from './useAuth';

// Pages Django serves itself (reached through the Vite proxy): leave the SPA to open them.
const SERVER_PAGES = /^\/(admin|accounts)\//;

// Where to go after signing in: the page RequireAuth stopped, or Django's ?next= (same site only), else home.
function destination(location, searchParams) {
  const from = location.state?.from;
  if (from?.pathname && from.pathname !== '/login') return `${from.pathname}${from.search || ''}${from.hash || ''}`;
  const next = searchParams.get('next') || '';
  if (next.startsWith('/') && !next.startsWith('//')) return next;
  return '/';
}

function ServerRedirect({ to }) {
  useEffect(() => {
    window.location.replace(to);
  }, [to]);
  return <Loading />;
}

/**
 * Sign in (plan.md §8.2; LoginForm.jsx at 891f1b3): the old card with username, password and Sign in, the server's
 * message on failure, and under the button "Forgot your password? Ask an admin to reset it." No top bar (§8.1).
 * With Microsoft 365 sign-in set up (slice 47), "Sign in with Microsoft" comes first; once the PHI gate turns
 * passwords off it is the only way in. A refused Microsoft 365 sign-in lands here as ?signin=<code>.
 */
export default function LoginPage() {
  const { user, status, signIn } = useAuth();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [missing, setMissing] = useState('');
  const submit = useMutation({ mutationFn: signIn });
  const options = useQuery({ queryKey: ['auth', 'options'], queryFn: getSignInOptions, staleTime: Infinity });
  const microsoft = options.data?.microsoft;
  const passwords = options.data?.password ?? true;

  useEffect(() => {
    document.title = 'Sign in — 2Vantage';
  }, []);

  if (status === 'loading') return <Loading label="Checking sign-in…" />;
  if (user) {
    const target = destination(location, searchParams);
    return SERVER_PAGES.test(target) ? <ServerRedirect to={target} /> : <Navigate to={target} replace />;
  }

  function onSubmit(event) {
    event.preventDefault();
    if (!username.trim() || !password) {
      setMissing('Enter your username and password.');
      return;
    }
    setMissing('');
    submit.mutate({ username: username.trim(), password });
  }

  const refused = microsoft?.messages?.[searchParams.get('signin')] || '';
  const message = missing || (submit.isError ? errorText(submit.error) : '') || refused;

  // `.page-container > .card > form > .btn-primary` is where the old full-width button rule applies (O.5).
  return (
    <div className="page-container">
      <main className="card" aria-labelledby="login-title">
        <h2 id="login-title">Sign in</h2>
        {message && (
          <div role="alert" className="error-message">
            {message}
          </div>
        )}
        {microsoft && <MicrosoftSignIn start={microsoft.start} next={destination(location, searchParams)} />}
        {microsoft && passwords && (
          <div className="form-footer">
            <p>Or sign in with your username and password.</p>
          </div>
        )}
        {passwords && (
          <form onSubmit={onSubmit} noValidate>
            <div className="form-group">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                type="text"
                name="username"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </div>
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={submit.isPending}>
              Sign in
            </button>
          </form>
        )}
        {passwords && (
          <div className="form-footer">
            <p>Forgot your password? Ask an admin to reset it.</p>
          </div>
        )}
      </main>
    </div>
  );
}
