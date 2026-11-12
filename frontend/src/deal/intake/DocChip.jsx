import { useState } from 'react';
import cx from '../../ui/cx';

/*
 * One document chip on a coverage row (B21; old `CoverageIntentPanel.jsx`, 891f1b3): "✓ Invoice" opens the file in
 * Documents and its caret opens the picker; "↑ Invoice" (none on file) opens the picker. A file dropped from the
 * computer onto the chip uploads with its kind and the line in one request. Only file drags count.
 */
const hasFiles = (event) => Array.from(event.dataTransfer?.types || []).includes('Files');

export default function DocChip({ kind, label, ids, open, disabled, onPick, onOpenDoc, onDropFile, children }) {
  const [over, setOver] = useState(false);
  const drop = disabled
    ? {}
    : {
        onDragOver: (event) => {
          if (!hasFiles(event)) return;
          event.preventDefault();
          event.dataTransfer.dropEffect = 'copy';
          setOver(true);
        },
        onDragLeave: () => setOver(false),
        onDrop: (event) => {
          if (!hasFiles(event)) return;
          event.preventDefault();
          setOver(false);
          const [file] = Array.from(event.dataTransfer.files || []);
          if (file) onDropFile(file);
        },
      };
  const pickerProps = (event) => onPick(open ? null : event.currentTarget.closest('.bnf-cvg-chipwrap'));
  const lower = label.toLowerCase();
  return (
    <span className={cx('bnf-cvg-chipwrap', over && 'is-dropping')} data-kind={kind} {...drop}>
      {ids.length > 0 ? (
        <span className="bnf-cvg-chip is-on is-split">
          <button
            type="button"
            className="bnf-cvg-chipmain"
            title={`Open the ${lower} in Documents`}
            onClick={() => onOpenDoc(ids[0])}
          >
            ✓ {label}
            {ids.length > 1 ? ` ${ids.length}` : ''}
          </button>
          <button
            type="button"
            className="bnf-cvg-chipcaret"
            title="Change which file this is, or which lines it covers"
            aria-label={`Change the ${lower}`}
            aria-expanded={open}
            onClick={pickerProps}
          >
            ▾
          </button>
        </span>
      ) : (
        <button
          type="button"
          className="bnf-cvg-chip is-btn is-off"
          title={`No ${lower} for this line — pick a file, or drop one here`}
          aria-expanded={open}
          onClick={pickerProps}
        >
          {over ? 'Drop here' : `↑ ${label}`}
        </button>
      )}
      {children}
    </span>
  );
}
