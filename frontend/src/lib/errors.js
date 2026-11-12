// Turns any API error into display text (plan.md §3.6 error shapes).
//   {"field": ["msg"]}  ·  {"non_field_errors": ["msg"]}  ·  {"detail": "msg"}  ·  nested dicts and lists

const STATUS_TEXT = {
  401: 'You are signed out. Sign in again.',
  403: 'You do not have permission to do that.',
  404: 'Not found.',
  409: 'That conflicts with the current state. Refresh and try again.',
  410: 'This link has expired or was revoked.',
  413: 'The file is too large (50 MB at most).',
  429: 'Too many requests. Wait a moment and try again.',
};

export function humanize(key) {
  const text = String(key).replace(/_/g, ' ').trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function isPlainBody(data) {
  return Boolean(data) && typeof data === 'object' && !(typeof Blob !== 'undefined' && data instanceof Blob);
}

function joinMessages(value) {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(joinMessages).filter(Boolean).join(' ');
  if (typeof value === 'object') return flatten(value).join(' ');
  return String(value);
}

// Every message in a DRF error body, field names prefixed (labels maps field keys to display labels).
function flatten(data, labels = {}) {
  if (typeof data === 'string') return [data];
  if (Array.isArray(data)) {
    return data.flatMap((item, index) =>
      item && typeof item === 'object' && !Array.isArray(item)
        ? flatten(item, labels).map((msg) => `Row ${index + 1}: ${msg}`)
        : flatten(item, labels),
    );
  }
  if (!data || typeof data !== 'object') return [];
  const out = [];
  for (const [key, value] of Object.entries(data)) {
    const text = joinMessages(value);
    if (!text) continue;
    if (key === 'detail' || key === 'non_field_errors') out.push(text);
    else out.push(`${labels[key] || humanize(key)}: ${text}`);
  }
  return out;
}

export function errorStatus(error) {
  return error?.response?.status ?? null;
}

function detailOf(error) {
  const data = error?.response?.data;
  return isPlainBody(data) && typeof data.detail === 'string' ? data.detail : '';
}

// DRF answers 403 "Authentication credentials were not provided." when SessionAuthentication finds no session.
export function isSignedOutError(error) {
  const status = errorStatus(error);
  if (status === 401) return true;
  return status === 403 && /credentials were not provided|not authenticated/i.test(detailOf(error));
}

export function isCsrfError(error) {
  return errorStatus(error) === 403 && /csrf/i.test(detailOf(error));
}

/** Display text for any error: an axios error, a DRF body, an Error, or a string. */
export function errorText(error, { fallback = 'Something went wrong. Try again.', labels } = {}) {
  if (!error) return '';
  if (typeof error === 'string') return error;
  if (error.isAxiosError || error.response || error.request) {
    if (!error.response) {
      return error.code === 'ECONNABORTED'
        ? 'The server took too long to answer. Try again.'
        : 'Cannot reach the server. Check your connection and try again.';
    }
    const { status, data } = error.response;
    if (isPlainBody(data)) {
      const messages = flatten(data, labels);
      if (messages.length) return messages.join(' ');
    }
    if (status >= 500) return `The server had a problem (${status}). Try again; if it keeps happening, tell an admin.`;
    return STATUS_TEXT[status] || fallback;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

/** Per-field messages ({field: "msg"}) so a save error can appear where the value was typed. */
export function fieldErrors(error) {
  const data = error?.response?.data;
  if (!isPlainBody(data) || Array.isArray(data)) return {};
  const out = {};
  for (const [key, value] of Object.entries(data)) {
    if (key === 'detail' || key === 'non_field_errors') continue;
    const text = joinMessages(value);
    if (text) out[key] = text;
  }
  return out;
}

/**
 * Text for the messages NOT shown beside a field: whole-request messages plus errors for fields the form does
 * not display. Pass the field keys the form shows next to their inputs.
 */
export function formErrorText(error, shownFields = []) {
  if (!error) return '';
  const data = error?.response?.data;
  if (isPlainBody(data) && !Array.isArray(data)) {
    const rest = Object.fromEntries(Object.entries(data).filter(([key]) => !shownFields.includes(key)));
    const messages = flatten(rest);
    if (messages.length || Object.keys(data).length) return messages.join(' ');
  }
  return errorText(error);
}
