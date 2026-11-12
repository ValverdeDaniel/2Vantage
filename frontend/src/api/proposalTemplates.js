// Saved parts of a proposal, Mine and Shared (plan.md §7.12 `proposal/templates/`; J68, OQ7). Firm rows, not deal
// rows: query key ['proposal-templates', kind, line]. A template is {id, name, description, kind, line ('' = any
// line), config ({path: value}), shared, owner_id, owner_name, is_mine, can_edit, built_in, updated_at}; the built-in
// "Vantage default" (kind layout) comes first and is never changed. Applying one is the builder's own PATCH.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';

const KEY = ['proposal-templates'];

export function useTemplates(kind, line) {
  return useQuery({
    queryKey: [...KEY, kind, line ?? ''],
    queryFn: async () => (await api.get('proposal/templates/', { params: { kind, line: line || undefined } })).data,
    staleTime: 0,
    enabled: Boolean(kind),
  });
}

/** ＋ Save as template ({name, description, kind, line, shared, config}) or Update ({id, …changes}) → the template.
 *  A 400 names each refused field ({name: '…'}). */
export function useSaveTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }) =>
      id ? (await api.patch(`proposal/templates/${id}/`, body)).data : (await api.post('proposal/templates/', body)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  });
}

/** Delete (its owner or an admin). */
export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id) => api.delete(`proposal/templates/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  });
}
