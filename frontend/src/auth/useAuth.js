import { createContext, useContext } from 'react';

export const AuthContext = createContext(null);

/**
 * { user, status: 'loading' | 'ready' | 'error', error, retry(), signIn({username, password}), signOut(),
 *   signedOutOnPurpose }. user is null when signed out.
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth() needs <AuthProvider> above it.');
  return context;
}
