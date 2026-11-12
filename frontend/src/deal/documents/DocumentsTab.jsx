import { useState } from 'react';
import { downloadUrl, useDeleteDocument, useDocuments, useUpdateDocument, useUploadDocument } from '../../api/documents';
import { useMeta } from '../../api/meta';
import { downloadFile } from '../../lib/download';
import { errorText } from '../../lib/errors';
import ConfirmDialog from '../../ui/ConfirmDialog';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import Select from '../../ui/Select';
import { useToast } from '../../ui/useToast';
import { EditDialog, UploadDialog } from './DocumentDialogs';
import DocumentsTable from './DocumentsTable';

/**
 * Documents, version 1 (plan.md §8.16): every file on the deal, until slice 15 brings the old station. The old tab's
 * title, subtitle row (`bnf-doc-adder`) and panel hold 2V's table, on the old archived-list table (E1–E8 wait).
 */
export default function DocumentsTab({ deal }) {
  const toast = useToast();
  const { data: meta } = useMeta();
  const documents = useDocuments(deal.id);
  const upload = useUploadDocument(deal.id);
  const update = useUpdateDocument(deal.id);
  const remove = useDeleteDocument(deal.id);
  const [kind, setKind] = useState('');
  const [uploading, setUploading] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);

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

  const rows = documents.data.filter((doc) => !kind || doc.kind === kind);

  async function download(doc) {
    try {
      await downloadFile(downloadUrl(doc.id));
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  async function confirmDelete() {
    try {
      await remove.mutateAsync(deleting.id);
      toast.success('Document deleted');
    } catch (error) {
      toast.error(errorText(error));
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="bb-tab-page">
      <div className="bb-tab-title">Documents</div>
      <div className="bb-subtitle bb-mb">
        Carrier quotes, renewals, SBCs and imported plan templates are kept here.
      </div>
      <div className="bnf-doc-adder">
        <label className="bb-drop-meta">
          Kind{' '}
          <Select
            className="bnf-select"
            value={kind}
            onChange={(event) => setKind(event.target.value)}
            options={[{ value: '', label: 'All kinds' }, ...meta.document_kinds.map((k) => ({ value: k.key, label: k.label }))]}
          />
        </label>
        <button type="button" className="btn btn-sm btn-primary" onClick={() => setUploading(true)}>
          Upload
        </button>
      </div>
      <div className="bb-panel">
        {!documents.data.length ? (
          <div className="empty-state">
            No documents yet — upload carrier quotes, renewals, SBCs or a plan template.
          </div>
        ) : (
          <DocumentsTable
            rows={rows}
            meta={meta}
            onDownload={download}
            onEdit={setEditing}
            onDelete={setDeleting}
          />
        )}
        {documents.data.length > 0 && !rows.length && <div className="empty-state">No documents of this kind.</div>}
      </div>
      <UploadDialog
        open={uploading}
        onClose={() => setUploading(false)}
        meta={meta}
        upload={upload}
        onDone={(count) => toast.success(`Uploaded ${count} file${count === 1 ? '' : 's'}`)}
      />
      <EditDialog document={editing} onClose={() => setEditing(null)} meta={meta} update={update} />
      <ConfirmDialog
        open={Boolean(deleting)}
        title="Delete this document?"
        message={deleting ? `${deleting.label || deleting.original_name} and its file are removed from the deal.` : ''}
        confirmLabel="Delete"
        tone="danger"
        busy={remove.isPending}
        onCancel={() => setDeleting(null)}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
