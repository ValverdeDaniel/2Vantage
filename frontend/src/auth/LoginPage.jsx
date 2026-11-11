import { useMutation } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Navigate, useLocation, useSearchParams } from 'react-router';
import { errorText } from '../lib/errors';
import Button from '../ui/Button';
import Field from '../ui/Field';
import { PageSpinner } from '../ui/Spinner';
import TextInput from '../ui/TextInput';
import styles from './LoginPage.module.css';
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
  return <PageSpinner />;
}

/** Sign in (plan.md §8.2): username, password, the server's message on failure. */
export default function LoginPage() {
  const { user, status, signIn } = useAuth();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [missing, setMissing] = useState('');
  const submit = useMutation({ mutationFn: signIn });

  useEffect(() => {
    document.title = 'Sign in — 2Vantage';
  }, []);

  if (status === 'loading') return <PageSpinner label="Checking sign-in…" />;
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

  const message = missing || (submit.isError ? errorText(submit.error) : '');

  return (
    <main className={styles.page}>
      <form className={styles.card} onSubmit={onSubmit} noValidate aria-labelledby="login-title">
        <p className={styles.brand}>2Vantage</p>
        <h1 id="login-title" className={styles.title}>
          Sign in
        </h1>
        <Field label="Username">
          <TextInput
            name="username"
            autoComplete="username"
            autoFocus
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </Field>
        <Field label="Password">
          <TextInput
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>
        {message && (
          <p role="alert" className={styles.error}>
            <span aria-hidden="true">⚠ </span>
            {message}
          </p>
        )}
        <Button type="submit" variant="primary" block busy={submit.isPending}>
          Sign in
        </Button>
        <p className={styles.help}>Forgot your password? Ask an admin to reset it.</p>
      </form>
    </main>
  );
}
