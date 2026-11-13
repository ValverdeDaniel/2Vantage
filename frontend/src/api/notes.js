// A deal's notes (plan.md §7.3; A37, M73–M77; deals' doors, slice 38). Query key ['deal', id, 'notes'] (staleTime 0).
// A write refetches the notes, the deal's activity (the drawer and the Overview's Timeline share the prefix) and the
// Overview, whose Last contact counts a logged call, email or meeting (M37). A delete answers its Activity row: its
// Revert is the Undo (M77; deals' `activity/{id}/revert/`).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey } from './deals';

export const notesKey = (dealId) => dealKey(dealId, 'notes');

/** GET deals/{id}/notes/ → [{id, deal_id, body, kind, kind_label, pinned, author, can_edit, created_at, updated_at}],
 *  pinned first, newest first; deleted notes are left out. */
export function useNotes(dealId) {
  return useQuery({
    queryKey: notesKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/notes/`)).data,
    staleTime: 0,
    enabled: Boolean(dealId),
  });
}

function useNoteWrite(dealId, mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: () =>
      ['notes', 'activity', 'overview'].forEach((area) =>
        queryClient.invalidateQueries({ queryKey: dealKey(dealId, area) }),
      ),
  });
}

/** mutateAsync({body, kind}) — POST deals/{id}/notes/ → 201 note. 400 {body | kind: [sentence]}. */
export function useAddNote(dealId) {
  return useNoteWrite(dealId, async (body) => (await api.post(`deals/${dealId}/notes/`, body)).data);
}

/** mutateAsync({id, body?, kind?, pinned?}) — PATCH notes/{id}/ → note. 403 when not the author or an admin. */
export function useEditNote(dealId) {
  return useNoteWrite(dealId, async ({ id, ...changes }) => (await api.patch(`notes/${id}/`, changes)).data);
}

/** mutateAsync(id) — DELETE notes/{id}/ → {id, activity_id}: soft, and its Revert brings the note back. */
export function useDeleteNote(dealId) {
  return useNoteWrite(dealId, async (id) => (await api.delete(`notes/${id}/`)).data);
}
