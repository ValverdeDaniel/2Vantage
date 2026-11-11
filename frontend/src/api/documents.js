// Documents, version 1 (plan.md §7.4). Query key: ['deal', id, 'documents'].
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey, invalidateDeal } from './deals';

export const documentsKey = (dealId) => dealKey(dealId, 'documents');

export function useDocuments(dealId) {
  return useQuery({
    queryKey: documentsKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/documents/`)).data,
    staleTime: 0,
  });
}

/** ({file, kind, role, carrier, lines, label}) → document */
export function useUploadDocument(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, lines = [], ...meta }) => {
      const form = new FormData();
      form.append('file', file);
      Object.entries(meta).forEach(([key, value]) => value != null && form.append(key, value));
      form.append('lines', JSON.stringify(lines));
      return (await api.post(`deals/${dealId}/documents/`, form)).data;
    },
    onSuccess: () => invalidateDeal(queryClient, dealId),
  });
}

export function useUpdateDocument(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ documentId, changes }) => (await api.patch(`documents/${documentId}/`, changes)).data,
    onSuccess: () => invalidateDeal(queryClient, dealId),
  });
}

export function useDeleteDocument(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (documentId) => api.delete(`documents/${documentId}/`),
    onSuccess: () => invalidateDeal(queryClient, dealId),
  });
}

export function downloadUrl(documentId, { inline = false } = {}) {
  return `documents/${documentId}/download/${inline ? '?inline=1' : ''}`;
}
