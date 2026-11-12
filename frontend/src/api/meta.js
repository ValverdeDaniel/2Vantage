// GET /api/meta/ — every vocabulary (plan.md §7.1). Fetched once; the frontend never hard-codes these lists.
import { useQuery } from '@tanstack/react-query';
import api from './client';

export const META_KEY = ['meta'];

export async function getMeta() {
  const { data } = await api.get('meta/');
  return data;
}

/** {lines, tiers, stages, relationships, funding, document_kinds, document_roles, plans, carriers, board} — `board` is
 *  the Advisor's columns per line and preset, sorts, the transpose limit, sliders, budget rungs and compliance words. */
export function useMeta() {
  return useQuery({ queryKey: META_KEY, queryFn: getMeta, staleTime: Infinity, gcTime: Infinity });
}

// Stage keys with their own behaviour (plan.md §5.1): lost is off the ladder; sold is reached only by a sale.
export const LOST = 'lost';
export const SOLD = 'sold';

// The status with its own home view (Prospects); every other status lists under Clients (OQ101 c).
export const PROSPECT = 'prospect';

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

/** The client statuses (plan.md §5.1), [{key, label, create}]; screens say "Status". */
export function relationships(meta) {
  return meta?.relationships || [];
}

/** The statuses a new client may start with (Prospect, Existing client): the server's `create` flag. */
export function creatableStatuses(meta) {
  return relationships(meta).filter((status) => status.create);
}

/** The statuses the Clients view lists (New client, Existing client): every status but Prospect, in meta order. */
export function clientStatuses(meta) {
  return relationships(meta).filter((status) => status.key !== PROSPECT);
}

export function relationshipLabel(meta, key) {
  return labelOf(relationships(meta), key);
}
