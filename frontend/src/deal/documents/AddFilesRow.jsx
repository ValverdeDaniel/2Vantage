import { useRef, useState } from 'react';
import { labelOf } from '../../api/meta';

/*
 * The row above the files (`bnf-doc-adder`; plan.md §8.16; E4, E20): "＋ Add files" (a chooser beside the drop, until
 * slice 20's Work with Claude drawer takes both), and, when the deal asks for two or more lines, the line picker for
 * quote scans, "All lines (label each plan)" by default: the page context the drawer reads (E20).
 */
const SCAN_LINE_HELP =
  'For quote scans: which line of business the quotes are for — it decides which fields the reader looks for';

export default function AddFilesRow({ lines, meta, onFiles }) {
  const picker = useRef(null);
  const [scanLine, setScanLine] = useState('');
  return (
    <div className="bnf-doc-adder">
      <button type="button" className="btn btn-sm btn-secondary" onClick={() => picker.current?.click()}>
        ＋ Add files
      </button>
      <input
        ref={picker}
        type="file"
        multiple
        hidden
        aria-label="Add files"
        onChange={(event) => {
          onFiles(Array.from(event.target.files || []));
          event.target.value = '';
        }}
      />
      {lines.length > 1 && (
        <select
          className="bnf-select"
          value={scanLine}
          aria-label="Line of business for quote scans"
          onChange={(event) => setScanLine(event.target.value)}
          title={SCAN_LINE_HELP}
        >
          <option value="">All lines (label each plan)</option>
          {lines.map((key) => (
            <option key={key} value={key}>
              {labelOf(meta.lines, key)}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
