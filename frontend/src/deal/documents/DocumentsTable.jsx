import { downloadUrl } from '../../api/documents';
import { labelOf } from '../../api/meta';
import { formatWhen, personName } from '../../lib/format';

function size(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

const HEADS = ['Name', 'Kind', 'Role', 'Carrier', 'Lines', 'From', 'Uploaded', 'Size'];

/** Documents v1's list (plan.md §8.16), on the old archived-list table (`bnf-archived-table`). */
export default function DocumentsTable({ rows, meta, onDownload, onEdit, onDelete }) {
  const lineLabels = (keys) => keys.map((key) => labelOf(meta.lines, key)).join(', ');
  return (
    <table className="bnf-archived-table">
      <thead>
        <tr>
          {HEADS.map((head) => (
            <th scope="col" key={head}>
              {head}
            </th>
          ))}
          <th scope="col" aria-label="Actions" />
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
            <td className="bb-account-sub">
              {personName(doc.uploaded_by, '')} {formatWhen(doc.uploaded_at)}
            </td>
            <td className="bb-mono">{size(doc.size)}</td>
            <td className="bnf-archived-act">
              <a
                className="btn btn-secondary btn-sm"
                href={`/api/${downloadUrl(doc.id, { inline: true })}`}
                target="_blank"
                rel="noopener"
              >
                View
              </a>{' '}
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => onDownload(doc)}>
                Download
              </button>{' '}
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => onEdit(doc)}>
                Edit
              </button>{' '}
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={doc.issued}
                title={doc.issued ? 'An issued proposal is kept.' : undefined}
                onClick={() => onDelete(doc)}
              >
                Delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
