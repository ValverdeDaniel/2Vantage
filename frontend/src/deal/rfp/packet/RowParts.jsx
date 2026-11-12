import cx from '../../../ui/cx';
import { isPick, pillWords, tickable, tickBody } from './packetModel';

/*
 * The parts every packet row shares (plan.md §8.12; K35–K37, K52; old CarriersTab.jsx Tick, RowNotes, ForCell and
 * RfpPill at 891f1b3, same classes and words): the tick, the notes that say why a row stands where it does, who it is
 * for, and its check pill.
 */

/* One row's tick (K35); a row that cannot be built yet is greyed (K41); a download-only row has a dash (K42). */
export function Tick({ row, onSet }) {
  if (row.packet_eligible === false) {
    return (
      <span className="bnf-rfp-download-only" title="Download only — never zipped into the packet">
        —
      </span>
    );
  }
  const off = !tickable(row);
  return (
    <label
      className={cx('bnf-rfp-include', off && 'bnf-rfp-include-off')}
      data-guide={`rfp-include-${row.key}`}
      title={off ? 'Not ready to build yet' : 'In the packet'}
    >
      <input
        type="checkbox"
        checked={Boolean(row.include)}
        disabled={off}
        aria-label={`${row.title || row.label} in the packet`}
        onChange={(event) => onSet(tickBody(row, event.target.checked))}
      />
    </label>
  );
}

/* What a row is and why it stands where it does (K37): "your pick", "Off on purpose — …", "Ticked by hand — …". */
export function RowNotes({ row }) {
  return (
    <>
      {isPick(row) && (
        <span
          className="bnf-rfp-pick"
          title="Differs from what the carrier picks recommend — “Reset to recommended” puts it back"
        >
          your pick
        </span>
      )}
      {row.deliberate && (
        <div className="bnf-rfp-rownote bnf-rfp-rownote-deliberate">
          {row.include ? 'Ticked by hand — ' : 'Off on purpose — '}
          {row.deliberate}
        </div>
      )}
      {row.reason && <div className="bnf-rfp-rownote">{row.reason}</div>}
      {row.hint && <div className="bnf-rfp-rownote">💡 {row.hint}</div>}
      {row.capped && !row.alt_of && (
        <div className="bnf-rfp-rownote bb-amber">
          ⚠ The file has room for {row.max_rows} people; the last {row.rows - row.max_rows} on the census are not in it.
        </div>
      )}
    </>
  );
}

/* Who a row is for (K36): the carriers it reaches, else a word ("Any carrier", "Warner Pacific", …). */
export function ForCell({ row }) {
  if (row.required_by?.length) {
    return (
      <span className="bnf-rfp-for">
        {row.required_by.map((name) => (
          <span key={name} className="bnf-rfp-for-chip">
            {name}
          </span>
        ))}
      </span>
    );
  }
  return <span className="bb-muted">{row.for_fallback || '—'}</span>;
}

/* A row's check at a glance (K52): Ready, N problems, Not signed; the whole list opens before the download. */
export function CheckPill({ pill }) {
  const words = pillWords(pill);
  if (!words) return null;
  return <span className={cx('bnf-rfp-pill', words.ok ? 'bnf-rfp-pill-ok' : 'bnf-rfp-pill-warn')}>{words.text}</span>;
}
