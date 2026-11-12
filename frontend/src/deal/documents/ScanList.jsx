import { useMemo } from 'react';
import ReviewList from '../../valuereview/ReviewList';
import { checkLabel } from './checkWords';

/*
 * The Scanned data panel's List (plan.md §8.16, §10.7; E56–E59, D121, D122; slice 17): the values read from the files
 * in scope, worst first, with the bucket chips, the bulk bar with "Check this file" and ✦ Ask Claude to re-check (slice
 * 22), the keys and ↶ Undo. Every
 * review goes through the one marks door (`marks`, useMarks). With Find, the List marks and steps through the loaded
 * rows that match (E63); in Review mode a click opens the value in the file, the arrows follow, and E or a
 * double-click hands it to the Grid for editing (E65). `ref` takes the tab's keys (`act`) and the focus.
 */
export default function ScanList({
  ref,
  meta,
  scope,
  head,
  rows,
  sources,
  bucket,
  onBucket,
  marks,
  valueOf,
  activeRef,
  check,
  recheck,
  review,
  find,
  onOpen,
  onFollow,
  onEdit,
}) {
  const names = useMemo(() => new Map(scope.files.map((file) => [file.id, file.display_name])), [scope.files]);
  const many = scope.ids.length > 1;
  const words = many ? 'these files' : 'this file';
  const one = (action, row) => marks.run(action, { refs: [row.ref] }, { where: 'that value' });
  const listed = (action, list) =>
    marks.run(action, { refs: list.map((row) => row.ref) }, { where: bucket || find.only ? 'the values shown' : words });
  return (
    <ReviewList
      ref={ref}
      rows={rows}
      head={head}
      buckets={meta.review_buckets ?? []}
      filter={bucket}
      onFilter={onBucket}
      scopeWords={many ? 'these files' : `“${scope.name}”`}
      valueOf={valueOf}
      fileOf={(row) => (many ? names.get(row.doc) || '' : '')}
      activeRef={activeRef}
      onOpen={onOpen}
      onMark={listed}
      onMarkOne={one}
      busy={marks.busy}
      done={marks.last}
      onUndo={marks.undo}
      undoing={marks.undoing}
      more={{
        has: Boolean(sources.hasNextPage),
        loading: sources.isFetchingNextPage,
        load: () => sources.fetchNextPage(),
        pageSize: head.page_size,
      }}
      check={check && { busy: check.busy, run: check.check, label: checkLabel(scope.ids.length, false) }}
      recheck={recheck}
      find={find}
      review={review}
      onFollow={onFollow}
      onEdit={onEdit}
    />
  );
}
