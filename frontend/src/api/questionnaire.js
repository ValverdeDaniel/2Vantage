// The questionnaire (plan.md §7.9; G.6). Query keys ['deal', id, 'questionnaires'] (the deal's forms) and ['deal', id,
// 'questionnaire', form] (one form), staleTime 0 (deal tabs); the spec ['questionnaire-spec', form] is cached per version
// (the server answers it `private, max-age`). Every write answers the form as it now stands, so the form's cache takes
// the answer and nothing re-reads; the deal's other reads (the checklist, the sidebar's chips) refetch.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey, invalidateDeal } from './deals';

export const formsKey = (dealId) => dealKey(dealId, 'questionnaires');
export const formKey = (dealId, form) => dealKey(dealId, 'questionnaire', form);

/** GET deals/{id}/questionnaires/ → {forms: [{key, label, kind, item, armed, started, signed, progress}], items:
 * {item: {choice, form, source, needed, band, band_form, notice, label, signed}}, headcount, band}. */
export function useDealForms(dealId, { enabled = true } = {}) {
  return useQuery({
    queryKey: formsKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/questionnaires/`)).data,
    staleTime: 0,
    enabled: Boolean(dealId) && enabled,
  });
}

/** GET meta/questionnaires/{form}/ → the spec: sections, blocks, fields with their flags, options and tables. */
export function useSpec(form) {
  return useQuery({
    queryKey: ['questionnaire-spec', form],
    queryFn: async () => (await api.get(`meta/questionnaires/${form}/`)).data,
    staleTime: Infinity,
    enabled: Boolean(form),
  });
}

/** GET deals/{id}/questionnaires/{form}/ → {values, status, sources, rows, blocks, order, blanks, options, progress,
 * locked, officer, agent, reopens, item, cleared, waiting, …}. */
export function useQuestionnaire(dealId, form) {
  return useQuery({
    queryKey: formKey(dealId, form),
    queryFn: async () => (await api.get(`deals/${dealId}/questionnaires/${form}/`)).data,
    staleTime: 0,
    enabled: Boolean(dealId && form),
  });
}

// After a form's write: the form's cache takes the answer; the deal's other reads (its forms, the checklist) refetch,
// never the form itself (it is what the server just answered) nor the header (a questionnaire never moves it).
function adoptForm(queryClient, dealId, form, answer) {
  if (answer) queryClient.setQueryData(formKey(dealId, form), answer);
  queryClient.invalidateQueries({
    queryKey: dealKey(dealId),
    predicate: ({ queryKey }) => queryKey[2] !== 'header' && !(queryKey[2] === 'questionnaire' && queryKey[3] === form),
  });
}

// One serial scope per form: a form's writes land in the order they were made, and a switch waits for them (G35).
function useFormWrite(dealId, form, request) {
  const queryClient = useQueryClient();
  return useMutation({
    scope: { id: `questionnaire-${dealId}-${form}` },
    mutationFn: request,
    onSuccess: (answer) => adoptForm(queryClient, dealId, form, answer),
  });
}

/** mutate({answers: {slot: text}, relay?}) → the form, with `changed` slots and `dropped` [{slot, reason, options?}]. */
export function useSaveAnswers(dealId, form) {
  return useFormWrite(dealId, form, async (body) =>
    (await api.patch(`deals/${dealId}/questionnaires/${form}/answers/`, body)).data,
  );
}

/** mutate(block) → the form, with the new row's `row_id` (201). */
export function useAddRow(dealId, form) {
  return useFormWrite(dealId, form, async (block) =>
    (await api.post(`deals/${dealId}/questionnaires/${form}/rows/${block}/`)).data,
  );
}

/** mutate({block, rowId}) → the form. */
export function useRemoveRow(dealId, form) {
  return useFormWrite(dealId, form, async ({ block, rowId }) =>
    (await api.delete(`deals/${dealId}/questionnaires/${form}/rows/${block}/${rowId}/`)).data,
  );
}

/** mutate({who, name, authorized?, sign_anyway?}) → the form; 409 {detail, incomplete: {filled, total}} for blanks. */
export function useSign(dealId, form) {
  return useFormWrite(dealId, form, async (body) =>
    (await api.post(`deals/${dealId}/questionnaires/${form}/sign/`, body)).data,
  );
}

/** mutate(reason) → the form, reopened (G54). */
export function useReopen(dealId, form) {
  return useFormWrite(dealId, form, async (reason) =>
    (await api.post(`deals/${dealId}/questionnaires/${form}/reopen/`, { reason })).data,
  );
}

/** mutate({action, refs?}) → the form, with the `marked` slots (E103). */
export function useMarkAnswers(dealId, form) {
  return useFormWrite(dealId, form, async (body) =>
    (await api.post(`deals/${dealId}/questionnaires/${form}/marks/`, body)).data,
  );
}

/** mutate({item, choice}) → the deal's forms (G2): the checklist's pickers and the band notice's Keep and Switch. */
export function useChooseForm(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.patch(`deals/${dealId}/questionnaires/choice/`, body)).data,
    onSuccess: (answer) => {
      queryClient.setQueryData(formsKey(dealId), answer);
      queryClient.invalidateQueries({ queryKey: dealKey(dealId, 'questionnaire') });
      invalidateDeal(queryClient, dealId);
    },
  });
}
