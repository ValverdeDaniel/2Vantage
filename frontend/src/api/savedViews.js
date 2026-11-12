// The Advisor's saved board setups, Mine and Shared (plan.md §7.8 `saved-views/`; F28, OQ7). Firm rows, not deal
// rows: query key ['saved-views', view, line]. A setup is {id, name, description, view, line ('' = any line), shared,
// config, owner_id, owner_name, is_mine, can_edit, updated_at}.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';

const KEY = ['saved-views'];

/** The setups this person may use on `view`, offered on `line`: their own and the shared ones. */
export function useSavedViews(view, line) {
  return useQuery({
    queryKey: [...KEY, view, line],
    queryFn: async () => (await api.get('saved-views/', { params: { view, line } })).data,
    staleTime: 0,
    enabled: Boolean(view),
  });
}

/** ＋ Save current ({name, description, view, line, shared, config}) or Update ({id, …changes}) → the setup. A 400
 *  names each refused field ({name: '…', config: {…}}). */
export function useSaveView() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }) =>
      id ? (await api.patch(`saved-views/${id}/`, body)).data : (await api.post('saved-views/', body)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  });
}

/** Delete (its owner or an admin). */
export function useDeleteView() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id) => api.delete(`saved-views/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  });
}
