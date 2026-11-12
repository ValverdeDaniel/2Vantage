// Display formats (plan.md §3.6, §5.4). Dates MM/DD/YYYY; money $1,500; rates $512.34; percent +8.0%.
// Times show in the browser's time zone (the agency's office).

const MINUS = '−';

function pad(n) {
  return String(n).padStart(2, '0');
}

/** A Date from 'YYYY-MM-DD' (a local calendar day, never shifted by time zone) or an ISO timestamp. */
export function toDate(value) {
  if (!value) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  const plain = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
  if (plain) return new Date(Number(plain[1]), Number(plain[2]) - 1, Number(plain[3]));
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/** '2027-01-01' or a timestamp → '01/01/2027'; empty → `empty`. */
export function formatDate(value, empty = '') {
  const date = toDate(value);
  if (!date) return empty;
  return `${pad(date.getMonth() + 1)}/${pad(date.getDate())}/${date.getFullYear()}`;
}

/** '3:04 PM' */
export function formatTime(value) {
  const date = toDate(value);
  if (!date) return '';
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

/** '11/10/2026 3:04 PM' */
export function formatDateTime(value) {
  const date = toDate(value);
  return date ? `${formatDate(date)} ${formatTime(date)}` : '';
}

function sameDay(a, b) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/** Last-updated style: 'Today 3:04 PM' · 'Yesterday' · '11/08/2026'. */
export function formatUpdated(value, now = new Date()) {
  const date = toDate(value);
  if (!date) return '';
  if (sameDay(date, now)) return `Today ${formatTime(date)}`;
  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
  if (sameDay(date, yesterday)) return 'Yesterday';
  return formatDate(date);
}

/** A moment in a log: 'Today 3:04 PM' · 'Yesterday 9:12 AM' · '11/08/2026 4:30 PM'. */
export function formatWhen(value, now = new Date()) {
  const date = toDate(value);
  if (!date) return '';
  const day = formatUpdated(date, now);
  if (day.startsWith('Today')) return day;
  return `${day} ${formatTime(date)}`;
}

function toNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = typeof value === 'number' ? value : Number(String(value).replace(/[$,%\s]/g, ''));
  return Number.isFinite(n) ? n : null;
}

function withSign(n, text, signed) {
  if (n < 0) return `${MINUS}${text}`;
  return signed && n > 0 ? `+${text}` : text;
}

/** Whole dollars: 1500 → '$1,500'; signed: 17280 → '+$17,280', -6000 → '−$6,000'. Blank → `empty`. */
export function formatMoney(value, { signed = false, empty = '' } = {}) {
  const n = toNumber(value);
  if (n === null) return empty;
  const rounded = Math.round(n);
  return withSign(rounded, `$${Math.abs(rounded).toLocaleString('en-US')}`, signed);
}

/** Rates, two decimals: 512.34 → '$512.34'. `decimals` up to 4 for rate4 values ('$0.185'). */
export function formatRate(value, { decimals = 2, empty = '' } = {}) {
  const n = toNumber(value);
  if (n === null) return empty;
  const text = Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: decimals });
  return withSign(n, `$${text}`, false);
}

/** Percentage points (8.0 means 8 %): '+8.0%', '−5.0%'. signed=false → '8.0%'. */
export function formatPercent(value, { signed = true, decimals = 1, empty = '' } = {}) {
  const n = toNumber(value);
  if (n === null) return empty;
  return withSign(n, `${Math.abs(n).toFixed(decimals)}%`, signed);
}

/** 'Dana Lee', or the fallback for a missing person. */
export function personName(person, fallback = 'Unassigned') {
  return person?.name || fallback;
}
