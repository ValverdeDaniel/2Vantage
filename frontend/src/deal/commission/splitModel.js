// The split editor's draft, pure (H12, H18–H20; 891f1b3 `overview/SplitsPanel.jsx`: emptyDraft, toLines, errFor).
// No math: shares, dollars and the house % come from the server's preview (rule 5).

const PRIMARY = 'primary';

/** The editor's draft from the payload's split: the primary's key and the other rows with their terms. */
export function draftFrom(split) {
  const rows = split?.rows || [];
  const primary = rows.find((row) => row.role === PRIMARY);
  return {
    primary: primary?.key || null,
    rows: rows
      .filter((row) => row.role !== PRIMARY)
      .map((row) => ({
        role: row.role,
        key: row.key,
        amount: row.amount || null,
        renewal_amount: row.renewal_amount ?? null,
        expires_after_years: row.expires_after_years ?? '',
        basis: row.basis || 'pool',
        works_it: Boolean(row.works_it),
        terms_open: termsSet(row),
      })),
  };
}

/** Whether a row carries terms beyond its amount (the old "terms •"). */
export function termsSet(row) {
  return Boolean(row.renewal_amount || row.expires_after_years || row.basis === 'gross');
}

/** A person key as the API names it: 'p12' → {party: 12}; 'u5' → {user: 5}; anything else → {}. */
export function person(key) {
  const match = /^([pu])(\d+)$/.exec(String(key || ''));
  if (!match) return {};
  return match[1] === 'p' ? { party: Number(match[2]) } : { user: Number(match[2]) };
}

/** The body's rows: the primary first (when picked), then the others in draft order (index + 1 on the server). */
export function rowsFor(draft) {
  const rows = draft.primary ? [{ ...person(draft.primary), role: PRIMARY }] : [];
  for (const row of draft.rows) {
    rows.push({
      ...person(row.key),
      role: row.role,
      amount: row.amount,
      renewal_amount: row.renewal_amount,
      expires_after_years: row.expires_after_years === '' ? null : row.expires_after_years,
      basis: row.basis,
      works_it: row.works_it,
    });
  }
  return rows;
}

/** Whether every row names someone, so a preview is worth asking for. */
export function complete(draft) {
  return Boolean(draft.primary || draft.rows.length) && draft.rows.every((row) => row.key);
}

const FIELDS = ['party', 'role', 'amount', 'renewal_amount', 'expires_after_years', 'basis'];

/** The first message for draft row `index` (`rows.<i>.<field>`, the primary taking index 0 when picked). */
export function rowError(errors, draft, index) {
  const at = draft.primary ? index + 1 : index;
  for (const field of FIELDS) {
    const found = errors?.[`rows.${at}.${field}`];
    if (found) return Array.isArray(found) ? found[0] : found;
  }
  return '';
}

/** A top-level message: 'primary' (also the primary row's own party error) or 'split_total'. */
export function topError(errors, draft, key) {
  const pick = (value) => (Array.isArray(value) ? value[0] : value) || '';
  if (key === PRIMARY) return pick(errors?.['rows.primary']) || (draft.primary ? pick(errors?.['rows.0.party']) : '');
  return pick(errors?.[`rows.${key}`]);
}

/** The preview's share for a person in a role (else for the person in any role), or null. */
export function shareFor(preview, key, role) {
  const shares = preview?.shares || [];
  return shares.find((share) => share.key === key && share.role === role) || shares.find((s) => s.key === key) || null;
}

export function setRow(draft, index, patch) {
  return { ...draft, rows: draft.rows.map((row, i) => (i === index ? { ...row, ...patch } : row)) };
}

export function addRow(draft, role) {
  const row = { role, key: null, amount: null, renewal_amount: null, expires_after_years: '', basis: 'pool' };
  return { ...draft, rows: [...draft.rows, { ...row, works_it: role === 'secondary', terms_open: false }] };
}

export function removeRow(draft, index) {
  return { ...draft, rows: draft.rows.filter((_row, i) => i !== index) };
}

/** Pick a person for a row: their default split fills an empty amount (H12). */
export function pickPerson(draft, index, key, people) {
  const found = people.find((entry) => entry.key === key);
  const patch = { key };
  if (found?.default_split?.type && !draft.rows[index].amount) patch.amount = found.default_split;
  return setRow(draft, index, patch);
}

/** A role change keeps the person only when the new role takes their kind (H12). */
export function changeRole(draft, index, role, people, roleKinds) {
  const current = people.find((entry) => entry.key === draft.rows[index].key);
  const keep = current && (roleKinds[role] || []).includes(current.kind);
  return setRow(draft, index, { role, key: keep ? current.key : null });
}

/** The keys already on the split, but for row `index` (the picker hides them). */
export function usedKeys(draft, index) {
  return [draft.primary, ...draft.rows.filter((_row, i) => i !== index).map((row) => row.key)].filter(Boolean);
}

/** The Save button's words (the old ones): the client, a deal's own split again, or the deal for the first time. */
export function saveLabel({ scope, source, clientOnly, saving }) {
  if (saving) return 'Saving…';
  if (clientOnly || scope === 'client') return 'Save for this client';
  return source === 'deal' ? 'Save changes' : 'Save for this deal';
}
