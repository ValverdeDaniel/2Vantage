import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ensureCsrf, getMe, login, logout, ME_KEY } from '../api/accounts';
import { setSignedOutHandler } from '../api/client';
import { isSignedOutError } from '../lib/errors';
import { AuthContext } from './useAuth';

// Start-up (plan.md §3.9): fetch the CSRF cookie once, then ask who is signed in. Signed out → null.
async function loadMe() {
  await ensureCsrf();
  try {
    return await getMe();
  } catch (error) {
    if (isSignedOutError(error)) return null;
    throw error;
  }
}

/** Holds the signed-in user (from GET auth/me/) and the sign-in / sign-out actions. Nothing goes in localStorage. */
export default function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const [signedOutOnPurpose, setSignedOutOnPurpose] = useState(false);
  const me = useQuery({ queryKey: ME_KEY, queryFn: loadMe, staleTime: Infinity, refetchOnWindowFocus: false });
  const user = me.data ?? null;

  // Any request that finds the session gone (expired, user deactivated) lands here: RequireAuth then sends the
  // browser to /login and back afterwards.
  useEffect(
    () => setSignedOutHandler(() => queryClient.setQueryData(ME_KEY, null)),
    [queryClient],
  );

  // Once signed out, drop everything cached for the previous session.
  useEffect(() => {
    if (me.isSuccess && me.data === null) {
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== ME_KEY[0] });
    }
  }, [me.isSuccess, me.data, queryClient]);

  const signIn = useCallback(
    async (credentials) => {
      const signedIn = await login(credentials);
      setSignedOutOnPurpose(false);
      queryClient.setQueryData(ME_KEY, signedIn);
      return signedIn;
    },
    [queryClient],
  );

  const signOut = useCallback(async () => {
    try {
      await logout();
    } finally {
      setSignedOutOnPurpose(true);
      queryClient.setQueryData(ME_KEY, null);
    }
  }, [queryClient]);

  let status = 'ready';
  if (me.isPending) status = 'loading';
  else if (me.isError) status = 'error';

  const { refetch } = me;
  const value = useMemo(
    () => ({ user, status, error: me.error, retry: refetch, signIn, signOut, signedOutOnPurpose }),
    [user, status, me.error, refetch, signIn, signOut, signedOutOnPurpose],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}
