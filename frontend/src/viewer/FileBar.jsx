import cx from '../ui/cx';

/*
 * The viewer's file bar (plan.md §8.16; E31, D-164): which file is on screen (name · bucket · page N of M) and, when
 * a value opened it, which value ("Opened to show <row · plan>") and what "Check this file" found for it (`note`:
 * {tone, text, title}; "Not in the file" in the old staged review's rose, slice 16). With `scope` (the file the
 * station's other panels are about, when it is not this one), the way back: "← Back to <file>".
 */
export default function FileBar({ document, bucket, page, what, note, scope, onBack }) {
  if (!document) return null;
  const name = document.display_name || document.original_name;
  const elsewhere = Boolean(scope && scope.id !== document.id);
  const of = document.page_count ? ` of ${document.page_count}` : '';
  const pages = document.shape === 'pdf' && page ? ` · page ${page}${of}` : '';
  return (
    <div className={cx('bnf-file-bar', (what || elsewhere) && 'is-elsewhere')} data-file-bar-doc={document.id}>
      <span className="bnf-file-bar-name">📄 {name}</span>
      <span className="bnf-file-bar-meta">
        {bucket}
        {pages}
      </span>
      {what && <span className="bnf-file-bar-why">Opened to show {what}</span>}
      {what && note && (
        <span
          className={note.tone === 'absent' ? 'bnf-staged-absent' : 'bnf-file-bar-meta'}
          title={note.title}
          data-loc={note.tone}
        >
          {note.tone === 'absent' ? '⚠ ' : ''}
          {note.text}
        </span>
      )}
      {elsewhere && (
        <button type="button" className="btn btn-sm btn-secondary bnf-file-bar-back" onClick={onBack}>
          ← Back to {scope.display_name || scope.original_name}
        </button>
      )}
    </div>
  );
}
