// The questionnaire (plan.md §7.9; G.6). Query keys ['deal', id, 'questionnaires'] (the deal's forms) and ['deal', id,
// 'questionnaire', form] (one form), staleTime 0 (deal tabs); the spec ['questionnaire-spec', form] is cached per version
// (the server answers it `private, max-age`). Every write answers the form as it now stands, so the form's cache takes
// the answer and nothing re-reads; the deal's other reads (the checklist, the sidebar's chips) refetch.
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { downloadFile } from '../lib/download';
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

// ---- The files and their check (plan.md §9.12; G56, G61–G67, G135) ----

const formPath = (dealId, form) => `deals/${dealId}/questionnaires/${form}/`;

/** GET …/{form}/check/ → {form, label, ok, problems: [{code, text, count, fix: {tab, form, view?}}], ack}. */
export async function fetchCheck(dealId, form) {
  return (await api.get(`${formPath(dealId, form)}check/`)).data;
}

/** "Check the form ▸" (G67): the check, read fresh each time the pane opens and after every write to the deal. */
export function useFormCheck(dealId, form, { enabled = true } = {}) {
  return useQuery({
    queryKey: dealKey(dealId, 'questionnaire-check', form),
    queryFn: () => fetchCheck(dealId, form),
    staleTime: 0,
    enabled: Boolean(dealId && form) && enabled,
  });
}

/** The filled form, or the filed signed copy once the officer signed, under the server's name (G62). With `ack`, a
 * check that changed since answers 409 {detail, report}: the caller shows the fresh report (G66). */
export function downloadFilled(dealId, form, ack) {
  return downloadFile(`${formPath(dealId, form)}pdf/`, { params: ack ? { ack } : undefined });
}

/** The carrier's bundled blank, nothing filled in (G61). */
export function downloadBlank(dealId, form) {
  return downloadFile(`${formPath(dealId, form)}blank/`);
}

/** The filled form for the PDF pane (inline; logged as a view, G63). */
export function previewUrl(dealId, form) {
  return `/api/${formPath(dealId, form)}pdf/?inline=1`;
}

// ---- Claude's reads of filled forms (plan.md §10.5; G99, slice 52) ----

/** GET deals/{id}/questionnaires/reads/{readId}/ for each staged read → [{id, form, label, job, document, status,
 * signed, entries: [{ref, kind, label, new, old, page, low, sensitive, state, tick, why, opens?, block?, block_label?,
 * number?, target_number?, values?}], counts}], read fresh (the entries are worked out against the form as it stands).
 * Use and Discard go through the read's job (api/ai.js). */
export function useStagedReads(dealId, readIds) {
  return useQueries({
    queries: (readIds || []).map((readId) => ({
      queryKey: dealKey(dealId, 'questionnaire-read', readId),
      queryFn: async () => (await api.get(`deals/${dealId}/questionnaires/reads/${readId}/`)).data,
      staleTime: 0,
      enabled: Boolean(dealId && readId),
    })),
  });
}
