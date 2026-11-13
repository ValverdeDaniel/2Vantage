// The deal Overview (plan.md §7.16, §8.6; M.6). Query key ['deal', id, 'overview'] (staleTime 0, a deal tab): a write
// anywhere on the deal refetches it through `invalidateDeal`. The Overview writes nothing of its own: each control
// calls its owner's door (deals, intake, the client status door), as the hooks below do.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey, invalidateDeal } from './deals';
import { patchAnswers } from './intake';

export const overviewKey = (dealId) => dealKey(dealId, 'overview');

/**
 * GET deals/{id}/overview/ → {deal_id, identity: {name, legal_name, legal_name_default, type, type_label, stage,
 * open_days, renews, owner}, client: {id, name, relationship, client_since, on_book, convert: {allowed, sentence} |
 * null}, renewal_offer: {premium_annual, pct_change, label} | null, facts: {fein, sic_code, situs_state,
 * employee_count, carrier, funding, agent_of_record: {value, default}, deal_size, in_force, contact}, tiles:
 * {plans_quoted, last_contact_at, expected_revenue}}. The Waiting banner and Intake complete read the shell's journey.
 */
export function useOverview(dealId) {
  return useQuery({
    queryKey: overviewKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/overview/`)).data,
    staleTime: 0,
  });
}

// Each fact's door (M24–M30): intake's answers, intake's coverage row (the medical incumbent while no current plan
// holds it), the client's contacts (the first edit adds an HR admin, M30). Afterwards the whole deal refetches.
async function writeFact(dealId, clientId, { kind, key, value, coverageId, contactId }) {
  if (kind === 'answer') return patchAnswers(dealId, { answers: { [key]: value === '' ? null : value } });
  if (kind === 'coverage') {
    if (coverageId) return (await api.patch(`coverage/${coverageId}/`, { [key]: value })).data;
    return (await api.post(`deals/${dealId}/coverage/`, { line: 'medical', in_force: true, [key]: value })).data;
  }
  if (contactId) return (await api.patch(`contacts/${contactId}/`, { [key]: value })).data;
  return (await api.post(`clients/${clientId}/contacts/`, { [key]: value })).data;
}

/** mutate({kind: 'answer' | 'coverage' | 'contact', key, value, coverageId?, contactId?}). A 400 reaches `error`. */
export function useFactWrite(deal) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fact) => writeFact(deal.id, deal.client.id, fact),
    onSettled: () => invalidateDeal(queryClient, deal.id),
  });
}
