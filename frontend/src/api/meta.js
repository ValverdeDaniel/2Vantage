// GET /api/meta/ — every vocabulary (plan.md §7.1). Fetched once; the frontend never hard-codes these lists.
import { useQuery } from '@tanstack/react-query';
import api from './client';

export const META_KEY = ['meta'];

export async function getMeta() {
  const { data } = await api.get('meta/');
  return data;
}

/** {lines, tiers, stages, funding, document_kinds, document_roles, plans:{groups, fields, line_groups}} */
export function useMeta() {
  return useQuery({ queryKey: META_KEY, queryFn: getMeta, staleTime: Infinity, gcTime: Infinity });
}

// Stage keys with their own behaviour (plan.md §5.1): lost is off the ladder; sold is reached only by a sale.
export const LOST = 'lost';
export const SOLD = 'sold';

/** Label of `key` in a [{key, label}] vocabulary, or the key itself. */
export function labelOf(list, key, field = 'label') {
  return list?.find((item) => item.key === key)?.[field] ?? key ?? '';
}

export function lineLabel(meta, key) {
  return labelOf(meta?.lines, key);
}

export function stageLabel(meta, key) {
  return labelOf(meta?.stages, key);
}

/** Intake → Quoting → Proposal → Sold (meta order, without lost). */
export function stageLadder(meta) {
  return (meta?.stages || []).filter((stage) => stage.key !== LOST);
}

/** Stages a person may set by hand: the ladder without sold. */
export function manualStages(meta) {
  return stageLadder(meta).filter((stage) => stage.key !== SOLD);
}

// /api/meta/ has no client-relationship vocabulary yet; use it as soon as it does.
const RELATIONSHIPS = [
  { key: 'new', label: 'New' },
  { key: 'existing', label: 'Existing' },
];

export function relationships(meta) {
  return meta?.relationships || RELATIONSHIPS;
}

export function relationshipLabel(meta, key) {
  return labelOf(relationships(meta), key);
}
