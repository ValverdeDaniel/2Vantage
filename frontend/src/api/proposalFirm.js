// The firm's cover images, pictures, pages and team (plan.md §7.12 `proposal/covers/`, `proposal/cover-images/`,
// `proposal/firm-pages/`, `proposal/team/`; J32–J35, J43, J155). Firm rows, not deal rows: query keys under
// ['proposal-firm', …]. Every write here also refetches the open builders (their ledger and `stamps.firm` read the
// firm), never a deal's other queries. Pictures are fetched by URL with the session cookie; none is a client surface.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';

const FIRM = ['proposal-firm'];
export const coversKey = [...FIRM, 'covers'];
export const firmPagesKey = [...FIRM, 'pages'];
export const teamKey = [...FIRM, 'team'];

/** The cover image's ≤600 px thumbnail, the stock picture's tile and a person's photo, as `<img src>`. */
export const coverThumbUrl = (id) => `/api/proposal/cover-images/${id}/thumb/`;
export const stockThumbUrl = (key) => `/api/proposal/pictures/${key}/thumb/`;
export const photoUrl = (id, version) => `/api/proposal/team/${id}/photo/?v=${version}`;

/** A key's tile: a stock key or "upload:<id>". */
export function pictureThumbUrl(key) {
  const upload = /^upload:(\d+)$/.exec(key ?? '');
  return upload ? coverThumbUrl(upload[1]) : stockThumbUrl(key);
}

const refetchFirm = (queryClient, key) => {
  queryClient.invalidateQueries({ queryKey: key });
  queryClient.invalidateQueries({
    predicate: (query) => query.queryKey[0] === 'deal' && query.queryKey[2] === 'proposal' && query.queryKey.length === 3,
  });
};

function useFirmWrite(key, mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn, onSuccess: () => refetchFirm(queryClient, key) });
}

/** The firm's uploads in the tiles' order: [{id, key, label, width, height}]. */
export function useCoverImages() {
  return useQuery({ queryKey: coversKey, queryFn: async () => (await api.get('proposal/cover-images/')).data, staleTime: 0 });
}

/** ({file, label?}) → the upload; a refused file answers 400 {image: sentence}, past 24 a 409 sentence. */
export function useUploadCover() {
  return useFirmWrite(coversKey, async ({ file, label = '' }) => {
    const form = new FormData();
    form.append('image', file);
    if (label) form.append('label', label);
    return (await api.post('proposal/cover-images/', form)).data;
  });
}

/** (id) → deletes the upload for everyone; proposals that wear it fall back. */
export function useDeleteCover() {
  return useFirmWrite(coversKey, async (id) => api.delete(`proposal/cover-images/${id}/`));
}

/** The Cover card's tile PDF (one page a tile: Vantage, then each upload), for pdf.js. `picture`: a stock key or
 *  'none' (the first tile's picture). Kept while the uploads and the picture stay the same (the server's ETag). */
export function useCoverTiles(picture, version, enabled = true) {
  return useQuery({
    queryKey: [...FIRM, 'tiles', picture ?? '', version],
    queryFn: async ({ signal }) =>
      (await api.get('proposal/covers/', { params: { picture: picture ?? 'none' }, responseType: 'arraybuffer', signal }))
        .data,
    staleTime: Infinity,
    gcTime: 60 * 1000,
    retry: false,
    enabled,
  });
}

/** {about_text, about_stats, service_calendar}. */
export function useFirmPages(enabled = true) {
  return useQuery({
    queryKey: firmPagesKey,
    queryFn: async () => (await api.get('proposal/firm-pages/')).data,
    staleTime: 0,
    enabled,
  });
}

/** ({field: value}) → the firm pages; 400 names a refused field. */
export function useSaveFirmPages() {
  return useFirmWrite(firmPagesKey, async (changes) => (await api.patch('proposal/firm-pages/', changes)).data);
}

/** [person]: {id, name, title, group, phone, email, bio, on_by_default, sort_order, has_photo}, in order. */
export function useTeam(enabled = true) {
  return useQuery({ queryKey: teamKey, queryFn: async () => (await api.get('proposal/team/')).data, staleTime: 0, enabled });
}

/** The team's writes: add ({name}), save ({id, …changes}), remove (id), photo ({id, file}) and noPhoto (id). */
export function useTeamWrites() {
  return {
    add: useFirmWrite(teamKey, async (body) => (await api.post('proposal/team/', body)).data),
    save: useFirmWrite(teamKey, async ({ id, ...changes }) => (await api.patch(`proposal/team/${id}/`, changes)).data),
    remove: useFirmWrite(teamKey, async (id) => api.delete(`proposal/team/${id}/`)),
    photo: useFirmWrite(teamKey, async ({ id, file }) => {
      const form = new FormData();
      form.append('photo', file);
      return (await api.post(`proposal/team/${id}/photo/`, form)).data;
    }),
    noPhoto: useFirmWrite(teamKey, async (id) => (await api.delete(`proposal/team/${id}/photo/`)).data),
  };
}
