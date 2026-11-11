// Sign-in API (plan.md §7.2). user = {id, username, first_name, last_name, full_name, email, is_admin}.
import api, { ensureCsrf } from './client';

export const ME_KEY = ['auth', 'me'];

export { ensureCsrf };

/** The signed-in user; rejects with 401/403 when signed out. */
export async function getMe() {
  const { data } = await api.get('auth/me/');
  return data;
}

/** {username, password} → user. 400 {"non_field_errors": [...]} on bad credentials. */
export async function login(credentials) {
  const { data } = await api.post('auth/login/', credentials);
  return data;
}

export async function logout() {
  await api.post('auth/logout/');
}
