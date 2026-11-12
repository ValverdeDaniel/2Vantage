import cx from '../../../ui/cx';
import { FILES } from './exportFiles';

/*
 * The row of files at the head of each view's toolbar (plan.md §8.14; J105; the old ExportViewer FileChips at
 * 891f1b3): Excel, PowerPoint, Paper and PDF. A file whose view is not built yet shows greyed with "next", as the old
 * chips did for theirs.
 */
export default function FileChips({ file, onFile }) {
  return (
    <div className="bnf-xv-formats" role="group" aria-label="Export">
      {FILES.map((f) => (
        <button
          key={f.id}
          type="button"
          className={cx('bnf-viewtab', f.id === file && 'bnf-viewtab-on', !f.live && 'bnf-xv-soon')}
          disabled={!f.live}
          aria-pressed={f.live ? f.id === file : undefined}
          onClick={() => f.live && f.id !== file && onFile(f.id)}
          title={f.live ? f.title : `${f.label}: coming next`}
        >
          {f.label}
          {!f.live && <span className="bnf-xv-soon-tag">next</span>}
        </button>
      ))}
    </div>
  );
}
