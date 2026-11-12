// Signing in to each app and finding a golden deal in it, over the apps' own APIs.
// Old Vantage keeps a DRF token in localStorage (as devtools/e2e/_lib.mjs at 891f1b3 does); 2Vantage uses Django's
// session cookie with CSRF (plan.md §3.8).

import { NEW, OLD } from './config.mjs';

async function getJson(url, headers) {
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error(`GET ${url} answered ${res.status}`);
  return res.json();
}

export async function oldSession() {
  const res = await fetch(`${OLD.api}/api/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: OLD.user, password: OLD.password }),
  }).catch((error) => ({ ok: false, status: error.message }));
  if (!res.ok) {
    throw new Error(`Old Vantage sign-in failed (${res.status}) at ${OLD.api}: start and load it first `
      + '(bash tools/parity/parity.sh up && bash tools/parity/parity.sh load).');
  }
  const { token } = await res.json();
  const headers = { Authorization: `Token ${token}` };
  return { app: OLD, token, get: (url) => getJson(`${OLD.api}${url}`, headers) };
}

export async function newSession() {
  const jar = new Map();
  const keep = (res) => {
    for (const line of res.headers.getSetCookie()) {
      const [pair] = line.split(';');
      const at = pair.indexOf('=');
      jar.set(pair.slice(0, at).trim(), pair.slice(at + 1));
    }
    return res;
  };
  const cookie = () => [...jar].map(([name, value]) => `${name}=${value}`).join('; ');
  keep(await fetch(`${NEW.base}/api/auth/csrf/`));
  const res = keep(await fetch(`${NEW.base}/api/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': jar.get('csrftoken') || '', Cookie: cookie() },
    body: JSON.stringify({ username: NEW.user, password: NEW.password }),
  }));
  if (!res.ok) {
    throw new Error(`2Vantage sign-in as ${NEW.user} failed (${res.status}) at ${NEW.base}: `
      + 'set LOOK_NEW_USER and LOOK_NEW_PASSWORD to a local superuser.');
  }
  return { app: NEW, cookies: jar, get: (url) => getJson(`${NEW.base}${url}`, { Cookie: cookie() }) };
}

export const session = (app) => (app === 'old' ? oldSession() : newSession());

// The golden deal's id in each app, found by its client's name (the spec's `client`).
export async function dealId(sess, client) {
  if (sess.app.name === 'old') {
    const hit = (await sess.get('/api/benefits/cases/')).find((row) => row.account_name === client);
    if (!hit) throw new Error(`Old Vantage has no "${client}": bash tools/parity/parity.sh load`);
    return hit.id;
  }
  const body = await sess.get(`/api/clients/?q=${encodeURIComponent(client)}`);
  const hit = (body.results || body).find((row) => row.name === client);
  if (!hit) throw new Error(`2Vantage has no "${client}": docker compose exec backend python manage.py seed_golden`);
  return hit.deal.id;
}

// Put the session into a browser context before its first page loads.
export async function signIn(context, sess) {
  if (sess.app.name === 'old') {
    await context.addInitScript((token) => {
      try {
        localStorage.setItem('token', token);
      } catch {
        // a sandboxed frame refuses storage; the app's own frame is what counts
      }
    }, sess.token);
    return;
  }
  await context.addCookies([...sess.cookies].map(([name, value]) => ({ name, value, url: NEW.base })));
}
