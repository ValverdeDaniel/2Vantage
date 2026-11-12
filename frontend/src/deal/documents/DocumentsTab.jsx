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
import { errorText, formErrorText } from '../../lib/errors';
import ConfirmDialog from '../../ui/ConfirmDialog';
import cx from '../../ui/cx';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import { useToast } from '../../ui/useToast';
import DocumentViewer from '../../viewer/DocumentViewer';
import FileBar from '../../viewer/FileBar';
import AddFilesRow from './AddFilesRow';
import FileAsList from './FileAsList';
import FileControls from './FileControls';
import FilePanel from './FilePanel';
import FileTabs from './FileTabs';
import RemovedFiles from './RemovedFiles';
import { chooseFile, inUploadOrder, proposalFiles } from './stationFiles';
import { sourceDocument, viewerFind } from './sourceTarget';
import useFileDrop from './useFileDrop';
import useStationState, { ALL_PROPOSALS } from './useStationState';

/*
 * The Documents tab (plan.md §8.16; Part E): every file on the deal, one on screen at a time, where a value opens with
 * its figure boxed (E1–E32). Slice 15 builds the file row, the File panel, Remove and "Show removed files", "File as"
 * by drop, the viewers and ↗'s deep links; the Scanned data panel beside the file (List, Grid, review) is slices
 * 17 and 23's, Re-read and the Claude drawer slices 19 and 20's, the pop-out window slice 65's.
 */
export default function DocumentsTab({ deal }) {
  const toast = useToast();
  const navigate = useNavigate();
  const { data: meta } = useMeta();
  const documents = useDocuments(deal.id);
  const removedQuery = useRemovedDocuments(deal.id);
  const station = useStationState();
  const value = useValueSource(station.ref);
  const upload = useUploadDocument(deal.id);
  const update = useUpdateDocument(deal.id);
  const archive = useArchiveDocument(deal.id);
  const restore = useArchiveDocument(deal.id, { restore: true });
  const [editing, setEditing] = useState(false);
  const [removing, setRemoving] = useState(null);
  const [pending, setPending] = useState([]);
  const [expanded, setExpanded] = useState(false);
  const [viewed, setViewed] = useState({ id: null, page: null }); // the page on screen, for the file bar
  const addPending = (chosen) => setPending((list) => [...list, ...chosen.map((file) => ({ file, kind: '' }))]);
  const drop = useFileDrop(addPending);

  const files = useMemo(() => inUploadOrder(documents.data), [documents.data]);
  const removed = removedQuery.data || [];
  const source = value.data?.source || null;
  const choice = chooseFile({
    asked: station.doc,
    files,
    removed,
    sourceDoc: sourceDocument(source),
    allKey: ALL_PROPOSALS,
  });
  const shown = choice.file;
  const showsValue = Boolean(shown && source && sourceDocument(source) === shown.id);
  const find = showsValue
    ? viewerFind(source, value.data.value, value.data.hint, station.page)
    : station.page
      ? { page: Number(station.page) }
      : {};

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

  const bucketLabel = (key) => labelOf(meta.document_buckets, key);
  const proposals = proposalFiles(files);

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

  const isRemoved = Boolean(shown?.archived_at);
  const removedList = (
    <RemovedFiles files={removed} busy={restore.isPending} onOpen={station.select} onRestore={putBack} />
  );
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
        className={cx('bb-policy-cols bnf-docs-cols', expanded && 'bnf-docs-expanded', drop.dropping && 'is-dropping')}
        {...drop.props}
      >
        <div className="bnf-docs-stack">
          <div className="bb-panel bb-policy-doc">
            {shown ? (
              <>
                <FileTabs
                  files={files}
                  shown={shown}
                  allOn={choice.all}
                  proposals={proposals}
                  bucketLabel={bucketLabel}
                  onSelect={station.select}
                  onAll={() => station.select(ALL_PROPOSALS)}
                  onDownload={download}
                />
                {removedList}
                <FileControls
                  file={shown}
                  editing={editing}
                  expanded={expanded}
                  onEdit={() => setEditing(true)}
                  onRemove={() => setRemoving(shown)}
                  onExpand={() => setExpanded((v) => !v)}
                />
                {editing && !isRemoved && (
                  <FilePanel
                    key={shown.id}
                    file={shown}
                    meta={meta}
                    saving={update.isPending}
                    error={update.error ? formErrorText(update.error) : ''}
                    onSave={save}
                    onCancel={() => {
                      update.reset();
                      setEditing(false);
                    }}
                  />
                )}
                <FileBar
                  document={shown}
                  bucket={isRemoved ? 'Removed' : bucketLabel(shown.bucket)}
                  page={(viewed.id === shown.id && viewed.page) || find.page || 1}
                  what={showsValue ? value.data.what : ''}
                />
                <DocumentViewer
                  document={shown}
                  find={find}
                  jumpKey={station.jumpKey}
                  onPageChange={(page) => setViewed({ id: shown.id, page })}
                  onDownload={download}
                />
              </>
            ) : (
              <>
                <div className="bb-subtitle">No documents yet — drop the carrier files anywhere on this tab.</div>
                {removedList}
              </>
            )}
          </div>
        </div>
      </div>
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
