import { useState } from 'react';
import BuilderCard from '../../shared/BuilderCard';
import CardStatsPicker from './CardStatsPicker';
import { groupRows, rowSections, rowsSummary, toggledRows } from './builderModel';

/*
 * What this section shows (plan.md §8.14; J59–J62; the old rows card at 891f1b3): the section's parts (Plan
 * comparison, Cost summary, Recommendation), the client-facing stop-loss row set, the note under the table (≤4 lines,
 * 600 characters, saved on blur), the plan cards' stats, and the benefit rows by group with all / none. Each control
 * writes one path of the line's settings (`lines.<line>.…`); `rows` null is every row with a value (the default) and
 * [] is "show no benefit rows". Only rows a client file may print are offered (no lasers, J.5 B3).
 */
export default function RowsCard({ line, card, meta, busy, onSet }) {
  const [note, setNote] = useState(null);
  const spec = line.spec;
  const keys = line.rows.map((row) => row.key);
  const picked = spec.rows == null ? null : new Set(spec.rows);
  const shown = (key) => picked == null || picked.has(key);
  const set = (name, value) => onSet(`lines.${line.line}.${name}`, value);
  const savedNote = spec.table_note ?? '';
  return (
    <BuilderCard guide="build-rows" title="What this section shows" summary={rowsSummary(spec, keys.length)} card={card}>
      <div className="bb-panel-sub">
        {picked == null
          ? 'Every benefit row that any plan has a value for — the default.'
          : `${picked.size} of ${keys.length} rows picked.`}{' '}
        A stop-loss section usually shows contract terms and costs only, never plan design.
      </div>
      <div className="bnf-build-parts">
        {meta.parts.map((part) => (
          <label key={part.key} className="bnf-filter-check">
            <input
              type="checkbox"
              disabled={busy}
              checked={spec.parts[part.key] !== false}
              onChange={() => set(`parts.${part.key}`, spec.parts[part.key] === false)}
            />
            {part.label}
          </label>
        ))}
        {line.preset && (
          <button
            type="button"
            className="btn btn-secondary btn-sm bnf-build-preset"
            disabled={busy}
            title={line.preset.description}
            onClick={() => set('rows', keys.filter((key) => line.preset.rows.includes(key)))}
          >
            {line.preset.label}
          </button>
        )}
      </div>
      <label className="bnf-build-tablenote">
        <span>Note under the table</span>
        <textarea
          rows={2}
          maxLength={meta.limits.table_note}
          disabled={busy}
          value={note ?? savedNote}
          placeholder="Printed under this line's plan table in the PDF, the PowerPoint and the spreadsheet. For example: * Value Choice specialists only."
          onChange={(event) => setNote(event.target.value)}
          onBlur={() => {
            if (note !== null && note.trim() !== savedNote) set('table_note', note.trim());
            setNote(null);
          }}
        />
      </label>
      <CardStatsPicker line={line} max={meta.limits.card_stats} busy={busy} onChange={(next) => set('card_stats', next)} />
      <div className="bnf-build-rowshead">
        <span className="bnf-build-rowgroup-title">Benefit rows</span>
        <span className="bnf-build-selectall">
          <button type="button" disabled={busy || picked == null} title="Back to every row with a value" onClick={() => set('rows', null)}>
            all
          </button>
          <button
            type="button"
            disabled={busy || (picked != null && picked.size === 0)}
            title="Untick every row, then pick the ones the client sees"
            onClick={() => set('rows', [])}
          >
            none
          </button>
        </span>
      </div>
      <div className="bnf-build-rows">
        {rowSections(line.rows).map((section) => {
          const groupKeys = section.rows.map((row) => row.key);
          return (
            <div key={section.group} className="bnf-build-rowgroup">
              <div className="bnf-build-rowgroup-title">
                {section.label}
                <span className="bnf-build-selectall">
                  <button
                    type="button"
                    disabled={busy || groupKeys.every(shown)}
                    title="Show every row in this group"
                    onClick={() => set('rows', groupRows(spec.rows, keys, groupKeys, true))}
                  >
                    all
                  </button>
                  <button
                    type="button"
                    disabled={busy || !groupKeys.some(shown)}
                    title="Drop this whole group from the section"
                    onClick={() => set('rows', groupRows(spec.rows, keys, groupKeys, false))}
                  >
                    none
                  </button>
                </span>
              </div>
              {section.rows.map((row) => (
                <label key={row.key} className="bnf-filter-check">
                  <input
                    type="checkbox"
                    disabled={busy}
                    checked={shown(row.key)}
                    onChange={() => set('rows', toggledRows(spec.rows, keys, row.key))}
                  />
                  {row.label}
                </label>
              ))}
            </div>
          );
        })}
      </div>
    </BuilderCard>
  );
}
