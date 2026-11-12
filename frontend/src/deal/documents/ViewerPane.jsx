import { labelOf } from '../../api/meta';
import { formErrorText } from '../../lib/errors';
import DocumentViewer from '../../viewer/DocumentViewer';
import FileBar from '../../viewer/FileBar';
import CheckStrip from './CheckStrip';
import { locWords } from './checkWords';
import FileControls from './FileControls';
import FilePanel from './FilePanel';
import FileTabs from './FileTabs';

/*
 * The file side of the station (plan.md §8.16; E1–E3, E10–E18, E21–E32, E59): the file row with 📚 All proposals,
 * "Show removed files", the file's controls, what "Check this file" is doing, the File panel, the file bar and the
 * viewer. `station` holds the files and what is on screen; `on` the handlers DocumentsTab owns.
 */
export default function ViewerPane({ station, meta, removedList, on }) {
  const { files, shown, allOn, proposals, editing, expanded, update, check, checking, value, find, viewedPage } = station;
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
        onEdit={on.edit}
        onRemove={on.remove}
        onExpand={on.expand}
      />
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
      <FileBar
        document={shown}
        bucket={isRemoved ? 'Removed' : bucketLabel(shown.bucket)}
        page={viewedPage || find.page || 1}
        what={value ? value.what : ''}
        note={value ? locWords(value.source.loc) : null}
      />
      <DocumentViewer
        document={shown}
        find={find}
        jumpKey={station.jumpKey}
        onPageChange={on.page}
        onDownload={on.download}
      />
    </div>
  );
}
