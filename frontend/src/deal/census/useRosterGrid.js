import { useEffect, useMemo, useRef } from 'react';
import useEditModePrompt from '../../grid/useEditModePrompt';
import useGridKeys from '../../grid/useGridKeys';
import { shownValue } from './rosterModel';

/*
 * The roster on the grid (plan.md §8.21; C4, C5; the old CensusGrid's useGridKeys and edit prompt): the keys walk
 * the people drawn (rows, by member id) and the columns shown (field keys); a commit and an undo go to the roster's
 * writes; a double-click outside ✎ Edit asks to enter it, then opens that cell. An editor opens on the value as the
 * grid shows it (a date MM/DD/YYYY, an SSN masked), so an unchanged cell writes nothing. `landOn(id, key)` puts the
 * cursor on a person just added (a dependent's First Name) once their row is drawn. The grid hooks know nothing about
 * people; this is where people meet them.
 */
export default function useRosterGrid({ members, fields, editing, writes, enterEdit, scrollRef }) {
  const rows = useMemo(() => members.map((member) => String(member.id)), [members]);
  const cols = useMemo(() => fields.map((field) => field.key), [fields]);
  const byId = useMemo(() => new Map(members.map((member) => [String(member.id), member])), [members]);
  const fieldOf = useMemo(() => new Map(fields.map((field) => [field.key, field])), [fields]);
  const landing = useRef(null); // {id, key}: a person just added, waiting for their row

  const grid = useGridKeys({
    enabled: editing,
    rows,
    cols,
    isEditable: (r, c) => byId.has(String(r)) && fieldOf.has(String(c)),
    valueAt: (r, c) => shownValue(fieldOf.get(String(c)) || {}, byId.get(String(r))?.values?.[c]),
    onCommit: (r, c, text, base) => writes.commit(Number(r), String(c), text, base),
    onUndo: () => {
      const went = writes.undo();
      return went ? { r: String(went.memberId), c: went.key } : null;
    },
    containerRef: scrollRef,
  });

  // A person just added: once their row is drawn, the cursor waits in `key` (else their first cell).
  const { select, focusGrid } = grid;
  useEffect(() => {
    const wanted = landing.current;
    if (!wanted || !editing || !byId.has(String(wanted.id))) return;
    landing.current = null;
    const key = cols.includes(wanted.key) ? wanted.key : cols[0];
    if (!key) return;
    select(String(wanted.id), key);
    focusGrid();
  }, [editing, byId, cols, select, focusGrid]);

  const prompt = useEditModePrompt({ on: !editing, enter: enterEdit, land: grid.editAt });
  return {
    grid,
    prompt,
    landOn: (id, key) => {
      landing.current = { id, key };
    },
  };
}
