import cx from '../../ui/cx';

/*
 * The file row (plan.md §8.16; E1–E3, E17): 📚 All proposals (N) with two or more proposal files, then one tab per
 * file in upload order with its bucket tag and its full name on hover, and "⬇ Download file" for the file on screen.
 * The proposal files under All proposals wear the in-scope tint. The old markup and classes (bb-doc-tab*, bnf-doc-*).
 */
export default function FileTabs({ files, shown, allOn, proposals, bucketLabel, onSelect, onAll, onDownload }) {
  const inScope = new Set(allOn ? proposals.map((file) => file.id) : []);
  return (
    <div className="bb-doc-tabs" role="tablist" aria-label="Files">
      {proposals.length > 1 && (
        <button
          type="button"
          role="tab"
          aria-selected={allOn}
          className={cx('bb-doc-tab bnf-doc-all', allOn && 'active')}
          onClick={onAll}
          title="Every proposal file at once"
        >
          <span className="bb-doc-tab-name">📚 All proposals ({proposals.length})</span>
        </button>
      )}
      {files.map((file) => {
        const active = !allOn && shown?.id === file.id;
        const name = file.display_name || file.original_name;
        const both = name !== file.original_name;
        return (
          <button
            key={file.id}
            type="button"
            role="tab"
            aria-selected={active}
            className={cx('bb-doc-tab', active && 'active', inScope.has(file.id) && 'bnf-doc-inscope')}
            data-doc-tab={file.id}
            onClick={() => onSelect(file.id)}
          >
            <span
              className="bb-doc-tab-name"
              title={both ? `${name}\nFile: ${file.original_name}` : name}
            >
              📄 {name}
            </span>
            {file.bucket && <span className="bnf-doc-bucket">{bucketLabel(file.bucket)}</span>}
          </button>
        );
      })}
      {shown && (
        <button
          type="button"
          className="bb-doc-open-link"
          onClick={onDownload}
          title="Download the original file as it was uploaded"
        >
          ⬇ Download file
        </button>
      )}
    </div>
  );
}
