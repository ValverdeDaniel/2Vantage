import { useQuery } from '@tanstack/react-query';
import api from '../api/client';
import { getFormSpec } from './portalApi';

/*
 * A form's spec on the client's page (plan.md §7.14; G.6 "the narrowed spec, cacheable per version"; slice 58): read
 * through the link once per version and kept. A preview (View as client, the request page's "their form") has no
 * token, and reads the staff copy instead — a person signed in sees the whole form anyway; the page shows only the
 * sections its state puts on screen.
 */
export default function useFormSpec(token, card) {
  return useQuery({
    queryKey: ['portal', token || 'preview', 'questionnaire-spec', card.form, card.version, card.narrowed],
    queryFn: async () =>
      token ? getFormSpec(token, card.form, card.version) : (await api.get(`meta/questionnaires/${card.form}/`)).data,
    staleTime: Infinity,
    retry: false,
    enabled: Boolean(card.state),
  });
}
