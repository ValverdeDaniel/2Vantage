// The one axios instance (plan.md §3.9). Session cookie + CSRF header; nothing about the session is stored locally.
import axios from 'axios';
import { isCsrfError, isSignedOutError } from '../lib/errors';

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});

let csrfRequest = null;

/** GET auth/csrf/ so the csrftoken cookie exists. Called once at start-up; `force` fetches a fresh one. */
export function ensureCsrf({ force = false } = {}) {
  if (force || !csrfRequest) {
    csrfRequest = api.get('auth/csrf/').then(
      () => undefined,
      (error) => {
        csrfRequest = null;
        throw error;
      },
    );
  }
  return csrfRequest;
}

// What to do when the session is gone. AuthProvider replaces this; the default is a hard redirect.
let signedOutHandler = () => {
  if (window.location.pathname !== '/login') window.location.assign('/login');
};

/** Registers the signed-out handler; returns a function that restores the previous one. */
export function setSignedOutHandler(handler) {
  const previous = signedOutHandler;
  signedOutHandler = handler;
  return () => {
    signedOutHandler = previous;
  };
}

// Answers from these are expected to say "not signed in"; the caller handles them (and the portal never redirects).
function isExempt(config) {
  const url = String(config?.url || '').replace(/^\/?(api\/)?/, '');
  return /^(auth\/(login|me|csrf)\/|portal\/)/.test(url);
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;
    // A 403 from a missing or stale CSRF cookie: fetch auth/csrf/ once and retry (plan.md §8.17).
    if (config && !config._csrfRetried && isCsrfError(error)) {
      config._csrfRetried = true;
      try {
        await ensureCsrf({ force: true });
      } catch {
        throw error;
      }
      return api.request(config);
    }
    if (isSignedOutError(error) && !isExempt(config)) signedOutHandler(error);
    throw error;
  },
);

export default api;
