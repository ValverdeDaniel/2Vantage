import { useState } from 'react';
import { downloadUrl, useDeleteDocument, useDocuments, useUpdateDocument, useUploadDocument } from '../../api/documents';
import { labelOf, useMeta } from '../../api/meta';
import { downloadFile } from '../../lib/download';
import { errorText } from '../../lib/errors';
import { formatWhen, personName } from '../../lib/format';
import Button from '../../ui/Button';
import ConfirmDialog from '../../ui/ConfirmDialog';
import EmptyState from '../../ui/EmptyState';
import InlineError from '../../ui/InlineError';
import Select from '../../ui/Select';
import Skeleton from '../../ui/Skeleton';
import { useToast } from '../../ui/useToast';
import { EditDialog, UploadDialog } from './DocumentDialogs';
import styles from './DocumentsTab.module.css';

function size(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** Documents, version 1 (plan.md §8.13): every file on the deal. */
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

  if (documents.isPending || !meta) return <Skeleton lines={5} height="18px" label="Loading documents…" />;
  if (documents.isError) return <InlineError error={documents.error} onRetry={() => documents.refetch()} />;

  const rows = documents.data.filter((doc) => !kind || doc.kind === kind);
  const lineLabels = (keys) => keys.map((key) => labelOf(meta.lines, key)).join(', ');

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
    <div className={styles.tab}>
      <div className={styles.toolbar}>
        <Button variant="primary" onClick={() => setUploading(true)}>
          Upload
        </Button>
        <label className={styles.filter}>
          Kind{' '}
          <Select
            size="sm"
            value={kind}
            onChange={(event) => setKind(event.target.value)}
            options={[{ value: '', label: 'All kinds' }, ...meta.document_kinds.map((k) => ({ value: k.key, label: k.label }))]}
          />
        </label>
      </div>
      {!documents.data.length ? (
        <EmptyState title="No documents yet" action={<Button onClick={() => setUploading(true)}>Upload</Button>}>
          Carrier quotes, renewals, SBCs and imported plan templates are kept here.
        </EmptyState>
      ) : (
        <div className={styles.scroll}>
          <table className={styles.table}>
            <thead>
              <tr>
                {['Name', 'Kind', 'Role', 'Carrier', 'Lines', 'From', 'Uploaded', 'Size', ''].map((head) => (
                  <th scope="col" key={head}>
                    {head}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((doc) => (
                <tr key={doc.id}>
                  <th scope="row">{doc.label || doc.original_name}</th>
                  <td>{labelOf(meta.document_kinds, doc.kind)}</td>
                  <td>{doc.role ? labelOf(meta.document_roles, doc.role) : ''}</td>
                  <td>{doc.carrier}</td>
                  <td>{lineLabels(doc.lines)}</td>
                  <td>{doc.source === 'client' ? `Client${doc.review_state ? ` (${doc.review_state})` : ''}` : 'Staff'}</td>
                  <td>
                    {personName(doc.uploaded_by, '')} {formatWhen(doc.uploaded_at)}
                  </td>
                  <td>{size(doc.size)}</td>
                  <td className={styles.actions}>
                    <Button size="sm" variant="ghost" as="a" href={`/api/${downloadUrl(doc.id, { inline: true })}`} target="_blank" rel="noopener">
                      View
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => download(doc)}>
                      Download
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setEditing(doc)}>
                      Edit
                    </Button>
                    <Button size="sm" variant="ghost" disabled={doc.issued} onClick={() => setDeleting(doc)}>
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && <p className={styles.muted}>No documents of this kind.</p>}
        </div>
      )}
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
