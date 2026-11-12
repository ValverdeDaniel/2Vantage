import { labelOf } from '../../api/meta';
import { formErrorText } from '../../lib/errors';
import DocumentViewer from '../../viewer/DocumentViewer';
import FileBar from '../../viewer/FileBar';
import CheckStrip from './CheckStrip';
import { locWords } from './checkWords';
import FileControls from './FileControls';
import FilePanel from './FilePanel';
import FileTabs from './FileTabs';
import RereadPanel from './RereadPanel';
import useReread from './useReread';

/*
 * The file side of the station (plan.md §8.16; E1–E3, E10–E18, E21–E32, E59, E75): the file row with 📚 All
 * proposals, "Show removed files", the file's controls and the Re-read panel under them (slice 19), what "Check this
 * file" is doing, the File panel, the file bar and the
 * viewer. `station` holds the files and what is on screen; `on` the handlers DocumentsTab owns. When a value read from
 * another file moved the viewer, the file bar says so and offers "← Back to <file>" (E31, D-164). While the file is
 * open in its own window (`popped`; E69), a slim bar stands in for the viewer: "Show the window", "Bring it back here".
 */
export default function ViewerPane({ station, meta, removedList, on }) {
  const { files, shown, allOn, proposals, editing, expanded, update, check, checking, value, find, viewedPage } = station;
  const { scopeFile, popped } = station;
  const reread = useReread(station.dealId, files, shown, allOn);
  const elsewhere = Boolean(scopeFile && scopeFile.id !== shown?.id);
  const bucketLabel = (key) => labelOf(meta.document_buckets, key);
  const isRemoved = Boolean(shown?.archived_at);
  if (!shown) {
    return (
      <div className="bb-panel bb-policy-doc">
        <div className="bb-subtitle">No documents yet — drop the carrier files anywhere on this tab.</div>
        {removedList}
      </div>
    );
  }
  return (
    <div className="bb-panel bb-policy-doc">
      <FileTabs
        files={files}
        shown={shown}
        allOn={allOn}
        proposals={proposals}
        bucketLabel={bucketLabel}
        onSelect={on.select}
        onAll={on.all}
        onDownload={on.download}
      />
      {removedList}
      <FileControls
        file={shown}
        editing={editing}
        expanded={expanded}
        popped={popped}
        reread={reread}
        onEdit={on.edit}
        onRemove={on.remove}
        onExpand={on.expand}
        onPopOut={on.popOut}
      />
      {reread.open && <RereadPanel reread={reread} />}
      <CheckStrip check={check} count={checking.length} />
      {editing && !isRemoved && (
        <FilePanel
          key={shown.id}
          file={shown}
          meta={meta}
          saving={update.isPending}
          error={update.error ? formErrorText(update.error) : ''}
          onSave={on.save}
          onCancel={on.cancelEdit}
        />
      )}
      {(!popped || elsewhere) && (
        <FileBar
          document={shown}
          bucket={isRemoved ? 'Removed' : bucketLabel(shown.bucket)}
          page={popped ? null : viewedPage || find.page || 1}
          away={popped}
          what={value ? value.what : ''}
          note={value ? locWords(value.source?.loc) : null}
          scope={scopeFile}
          onBack={on.back}
        />
      )}
      {popped ? (
        <div className="bnf-docs-poppedbar" role="status">
          <span>
            📄 <b>{shown.display_name || shown.original_name}</b> is open in its own window. Select a value and press F
            to show it there.
          </span>
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            onClick={on.showWindow}
            title="Bring the file's window to the front"
          >
            Show the window
          </button>
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            onClick={on.bringBack}
            title="Close the window and show the file here again"
          >
            Bring it back here
          </button>
        </div>
      ) : (
        <DocumentViewer
          document={shown}
          find={find}
          jumpKey={station.jumpKey}
          onPageChange={on.page}
          onDownload={on.download}
        />
      )}
    </div>
  );
}
