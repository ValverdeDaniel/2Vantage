// View as client (plan.md §8.1, §8.20; L78): a link's page for staff, read-only, through the signed-in API.
import { useQuery } from '@tanstack/react-query';
import api from './client';

export const previewKey = (linkId) => ['link', Number(linkId), 'preview'];

export function usePreviewLink(linkId) {
  return useQuery({
    queryKey: previewKey(linkId),
    queryFn: async () => (await api.get(`links/${Number(linkId)}/preview/`)).data,
    staleTime: 0,
    retry: false,
  });
}
