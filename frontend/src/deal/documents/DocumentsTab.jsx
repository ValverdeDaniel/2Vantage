import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  downloadUrl,
  useArchiveDocument,
  useDocuments,
  useRemovedDocuments,
  useUpdateDocument,
  useUploadDocument,
  useValueSource,
} from '../../api/documents';
import { labelOf, useMeta } from '../../api/meta';
import { downloadFile } from '../../lib/download';
import { errorText } from '../../lib/errors';
import ConfirmDialog from '../../ui/ConfirmDialog';
import cx from '../../ui/cx';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import { useToast } from '../../ui/useToast';
import { claudeDoor, ReadReviews } from '../claude';
import AddFilesRow from './AddFilesRow';
import FileAsList from './FileAsList';
import HistoryCard from './HistoryCard';
import RemovedFiles from './RemovedFiles';
import ScannedData from './ScannedData';
import { chooseFile, inUploadOrder, proposalFiles, scopeParam, stationScope } from './stationFiles';
import { sourceDocument, viewerFind } from './sourceTarget';
import useCheckFile from './useCheckFile';
import useFileDrop from './useFileDrop';
import useStationModes from './useStationModes';
import useStationState, { ALL_PROPOSALS } from './useStationState';
import useStationWindow from './useStationWindow';
import ViewerPane from './ViewerPane';

/*
 * The Documents tab (plan.md §8.16; Part E): every file on the deal, one on screen at a time, where a value opens with
 * its figure boxed (E1–E32), and beside it the Scanned data panel, where people check what was read from it (E34–E58;
 * slice 17). Slice 15 builds the file row, the File panel, Remove and "Show removed files", "File as" by drop, the
 * viewers and ↗'s deep links; slice 16 "Check this file" (the locator, a job in the worker); slice 17 the List with
 * its strip, keys and Undo, side by side with the file at 1,100 px, and the Change history card; slice 23 the Grid,
 * Find, Review mode and ✎ Edit, where F or a value followed in Review moves the viewer to the value's own file while
 * the panel keeps its files (`?list=`, D-164) and the file bar offers "← Back to" (E31); slice 65 the pop-out window
 * (useStationWindow) and census, intake and questionnaire files beside their owners' views; slice 19 ↻ Re-read… and
 * Claude's waiting reads under the station, used or undone here; slice 20 Work with Claude's drawer, which takes the
 * files dropped or added here.
 */
export default function DocumentsTab({ deal }) {
  const toast = useToast();
  const navigate = useNavigate();
  const { data: meta } = useMeta();
  const documents = useDocuments(deal.id);
  const removedQuery = useRemovedDocuments(deal.id);
  const station = useStationState();
  const modes = useStationModes(); // List or Grid, Review mode, ✎ Edit
  const value = useValueSource(station.ref, deal.id);
  const upload = useUploadDocument(deal.id);
  const update = useUpdateDocument(deal.id);
  const archive = useArchiveDocument(deal.id);
  const restore = useArchiveDocument(deal.id, { restore: true });
  const [editing, setEditing] = useState(false);
  const [removing, setRemoving] = useState(null);
  const [pending, setPending] = useState([]);
  const [expanded, setExpanded] = useState(false);
  const [viewed, setViewed] = useState({ id: null, page: null }); // the page on screen, for the file bar
  const filedHere = (chosen) => setPending((list) => [...list, ...chosen.map((file) => ({ file, kind: '' }))]);
  // With Claude set up, files dropped or added here go to Work with Claude's File room (D16); else they are filed here.
  const addPending = meta?.ai ? claudeDoor.attach : filedHere;
  const drop = useFileDrop(addPending);

  const files = useMemo(() => inUploadOrder(documents.data), [documents.data]);
  const removed = removedQuery.data || [];
  const source = value.data?.source || null;
  const choice = chooseFile({ asked: station.doc, files, removed, sourceDoc: sourceDocument(source), allKey: ALL_PROPOSALS });
  const shown = choice.file;
  const proposals = proposalFiles(files);
  // The Scanned data covers 📚 All proposals, or its own file, while the viewer shows the file a value opened (D-164).
  const scope = stationScope({ shown, all: choice.all, list: station.list, files, removed, allKey: ALL_PROPOSALS });
  const listAll = scope.all;
  const scopeFiles = scope.files;
  const checking = scopeFiles.map((file) => file.id);
  /** Open a value in its own file; the panel stays on its files (F, Enter, Review mode following a value). */
  const showValue = (docId, ref, options = {}) =>
    station.show(docId, ref, { ...options, list: scopeParam(scope, docId, ALL_PROPOSALS) });
  const check = useCheckFile(deal.id, checking);
  const showsValue = Boolean(shown && source && sourceDocument(source) === shown.id);
  const find = showsValue
    ? viewerFind(source, value.data.value, value.data.hint, station.page)
    : station.page
      ? { page: Number(station.page) }
      : {};

  // ⧉ New window (E69–E71; slice 65): the window shows what the viewer here would, and its keys act here.
  const win = useStationWindow({
    deal,
    shown,
    show: { find, what: showsValue ? value.data.what : '', scope: checking, jumpKey: station.jumpKey },
    on: { page: (id, page) => setViewed({ id, page }), open: (docId) => showValue(docId, '') },
  });

  // A link to a file the deal no longer has is said, never swapped silently (E18).
  const missingSaid = useRef('');
  useEffect(() => {
    if (choice.missing && documents.isSuccess && removedQuery.isSuccess && missingSaid.current !== station.doc) {
      missingSaid.current = station.doc;
      toast.error('That file is no longer on this deal.');
    }
  }, [choice.missing, documents.isSuccess, removedQuery.isSuccess, station.doc, toast]);

  useEffect(() => {
    if (!expanded) return undefined;
    const onKey = (event) => event.key === 'Escape' && setExpanded(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [expanded]);

  if (documents.isPending || !meta) return <Loading label="Loading the documents…" />;
  if (documents.isError) {
    return (
      <InlineError
        title="Could not load the documents."
        error={documents.error}
        onRetry={() => documents.refetch()}
        retrying={documents.isFetching}
      />
    );
  }

  const bucket = listAll ? 'proposal' : (scope.file ?? shown)?.bucket;
  const fileName = (id) => [...files, ...removed].find((file) => file.id === id)?.display_name || '';

  async function download() {
    try {
      await downloadFile(downloadUrl(shown.id));
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  async function save(changes) {
    try {
      await update.mutateAsync({ documentId: shown.id, changes });
      setEditing(false);
      toast.success(changes.kind !== shown.kind ? `Filed as ${labelOf(meta.document_kinds, changes.kind)}` : 'Saved');
    } catch {
      /* the panel stays open with the sentence (E11) */
    }
  }

  async function confirmRemove() {
    try {
      await archive.mutateAsync(removing.id);
      toast.success('Removed. "Show removed files" brings it back.');
      if (shown?.id === removing.id) station.select(files.find((f) => f.id !== removing.id)?.id ?? '');
    } catch (error) {
      toast.error(errorText(error));
    } finally {
      setRemoving(null);
    }
  }

  async function putBack(file) {
    try {
      await restore.mutateAsync(file.id);
      toast.success('Restored');
      station.select(file.id);
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  // Side by side with the file in List view, as the old station, and ▤ As in the file (slice 21); the Grid takes the
  // full width below (D-122).
  const beside = modes.view === 'file' || (modes.view === 'list' && !modes.editing);
  const listing = Boolean(shown && bucket === 'proposal' && beside);
  return (
    <div className="bb-tab-page">
      {station.back && (
        <button
          type="button"
          className="btn btn-sm btn-secondary bnf-back-review"
          onClick={() => navigate(`/deals/${deal.id}/review?${station.back}`)}
        >
          ‹ Back to review
        </button>
      )}
      <div className="bb-tab-title">Documents</div>
      <div className="bb-subtitle bb-mb">
        Every file on the deal. Pick a document to see it, or press ↗ on a value to see exactly where it came from. Drop
        files anywhere on this tab to add them.
      </div>
      <AddFilesRow lines={deal.requested_lines || []} meta={meta} onFiles={addPending} />
      <FileAsList
        pending={pending}
        meta={meta}
        upload={upload}
        onChange={setPending}
        onDone={(count) => toast.success(`Uploaded ${count} file${count === 1 ? '' : 's'}`)}
      />
      <div
        className={cx(
          'bb-policy-cols bnf-docs-cols',
          expanded && 'bnf-docs-expanded',
          drop.dropping && 'is-dropping',
          win.popped && 'bnf-docs-popped',
        )}
        {...drop.props}
      >
        <div className={cx('bnf-docs-stack', listing && 'bnf-docs-side')}>
          <ViewerPane
            meta={meta}
            removedList={
              <RemovedFiles files={removed} busy={restore.isPending} onOpen={station.select} onRestore={putBack} />
            }
            station={{
              dealId: deal.id,
              files,
              shown,
              allOn: listAll,
              proposals,
              editing,
              expanded,
              update,
              check,
              checking,
              find,
              jumpKey: station.jumpKey,
              value: showsValue ? value.data : null,
              viewedPage: viewed.id === shown?.id ? viewed.page : null,
              scopeFile: scope.file,
              popped: win.popped,
            }}
            on={{
              select: station.select,
              all: () => station.select(ALL_PROPOSALS),
              download,
              edit: () => setEditing(true),
              remove: () => setRemoving(shown),
              expand: () => setExpanded((v) => !v),
              save,
              cancelEdit: () => {
                update.reset();
                setEditing(false);
              },
              page: (page) => setViewed({ id: shown.id, page }),
              back: () => station.select(scope.file.id),
              popOut: win.popOut,
              showWindow: win.focus,
              bringBack: win.bringBack,
            }}
          />
          {shown && (
            <ScannedData
              key={checking.join(',')}
              deal={deal}
              meta={meta}
              scope={{
                ids: checking,
                files: scopeFiles,
                bucket,
                label: labelOf(meta.document_buckets, bucket),
                name: (scope.file ?? shown).display_name,
              }}
              expanded={expanded}
              modes={modes}
              viewer={{
                docId: shown.id,
                page: (viewed.id === shown.id && viewed.page) || station.page || '',
                ref: station.ref,
              }}
              onShow={showValue}
              check={(scope.file ?? shown).archived_at ? null : check}
            />
          )}
        </div>
      </div>
      {shown && (
        <ReadReviews dealId={deal.id} files={scopeFiles} onOpen={(docId, page) => showValue(docId, '', { page })} />
      )}
      <HistoryCard dealId={deal.id} fileName={fileName} />
      <ConfirmDialog
        open={Boolean(removing)}
        title="Remove this file?"
        message={
          removing
            ? `“${removing.display_name}” moves to "Show removed files", where it can be ` +
              'restored. Values read from it keep their link.'
            : ''
        }
        confirmLabel="Remove"
        tone="danger"
        busy={archive.isPending}
        onCancel={() => setRemoving(null)}
        onConfirm={confirmRemove}
      />
    </div>
  );
}
