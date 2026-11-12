/*
 * Which file the station shows (plan.md §8.16; E1–E3, E15, E18). Pure: the deal's files in, a choice out.
 * - The tabs run in upload order, oldest first (E1); each file's bucket is its kind's (the payload's `bucket`).
 * - 📚 All proposals appears with two or more proposal files (E3).
 * - With nothing asked, the station opens a file whose data is on screen: a proposal file, else a census, else the
 *   first (the old FIRST_DATA_DOC).
 * - A removed file still opens when a link or a value names it (values keep their link, E15); a file the deal no longer
 *   has is said, never swapped silently for another (E18).
 * - The Scanned data panel's scope is the viewer's file, every proposal file (📚, E3) or the file `?list=` names while
 *   the viewer shows a value read from another (D-164, E31): F moves the viewer, never the List or the Grid.
 */

export function inUploadOrder(files) {
  return [...(files || [])].sort((a, b) =>
    a.uploaded_at === b.uploaded_at ? a.id - b.id : a.uploaded_at < b.uploaded_at ? -1 : 1,
  );
}

export const proposalFiles = (files) => files.filter((file) => file.bucket === 'proposal');

export function firstDataFile(files) {
  const inBucket = (bucket) => files.find((file) => file.bucket === bucket);
  return inBucket('proposal') || inBucket('census') || files[0] || null;
}

/**
 * {file, all, missing}: the file to show for `asked` (an id, 'proposals' or ''), or for the value's `sourceDoc` when no
 * file is asked. `missing` is true when a file was named that neither list holds; the first data file shows instead.
 */
export function chooseFile({ asked, files, removed = [], sourceDoc = null, allKey = 'proposals' }) {
  if (asked === allKey) {
    const first = proposalFiles(files)[0];
    return { file: first || firstDataFile(files), all: Boolean(first), missing: false };
  }
  const wanted = Number(asked) || Number(sourceDoc) || null;
  if (wanted) {
    const file = files.find((f) => f.id === wanted) || removed.find((f) => f.id === wanted);
    if (file) return { file, all: false, missing: false };
    return { file: firstDataFile(files), all: false, missing: true };
  }
  return { file: firstDataFile(files), all: false, missing: false };
}

/**
 * {all, files, file}: what the Scanned data panel is about. `all` with 📚 All proposals (or `?list=proposals`) over
 * two or more proposal files; else the one file `?list=` names, or the file on screen (`file`).
 */
export function stationScope({ shown, all = false, list = '', files, removed = [], allKey = 'proposals' }) {
  const proposals = proposalFiles(files);
  if (all || (list === allKey && proposals.length > 1)) return { all: true, files: proposals, file: null };
  const id = Number(list) || null;
  const named = id ? files.find((f) => f.id === id) || removed.find((f) => f.id === id) : null;
  const file = named || shown || null;
  return { all: false, files: file ? [file] : [], file };
}

/** The `?list=` that keeps `scope` while the viewer moves to file `docId` ('' when they are one and the same). */
export function scopeParam(scope, docId, allKey = 'proposals') {
  if (scope.all) return allKey;
  return scope.file && scope.file.id !== Number(docId) ? String(scope.file.id) : '';
}
