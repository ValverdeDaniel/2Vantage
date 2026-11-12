import { useEffect, useRef, useState } from 'react';
import { draftOf, sameAnswer } from '../shared/fieldValue';
import { buildSections, nextRow, revealsOthers } from './formModel';
import useAnswerWrites from './useAnswerWrites';
import useIntakeKeys from './useIntakeKeys';

/*
 * The form's editing and keyboard flow (plan.md §8.9; B4, B5; D-161, D-205), ported from old Vantage 891f1b3
 * `IntakeTab.jsx` (`openField`, `closeField`, `commitField`, `onEditorKey`):
 * - a click opens an answer; text saves on blur, a select or date the mouse opened on the pick, a multi on Done;
 * - Enter saves and goes to the very next question, Tab to the next blank one this deal needs, Shift goes back; with
 *   nowhere to go the answer stays open, so the next press never falls to a button; Escape drops the draft;
 * - an answer opened by the keys is focused and selected, and holds a pick until Enter, Tab or a blur, so an arrow key
 *   never saves and closes it mid-flow;
 * - an answer other questions hang on waits for the server's reply before moving, since it alone says what the answer
 *   revealed; a click elsewhere meanwhile wins.
 * Enter and Tab with no answer open go on from the last answer opened (useIntakeKeys).
 */
const INSTANT = ['choice', 'yesno', 'multi', 'date'];
const HOLDS = ['choice', 'yesno', 'date'];

export default function useIntakeForm({ dealId, formMeta, data, enabled, relay, rootRef }) {
  const [editing, setEditing] = useState({ key: null, via: 'click' });
  const [drafts, setDrafts] = useState({});
  const editingRef = useRef(null); // the answer open NOW, for a blur or a reply that outlives its render
  const lastRef = useRef(null); // the last answer opened: where a press with none open goes on from
  const writes = useAnswerWrites(dealId, { relay });
  const sections = buildSections(formMeta, data);

  const open = (key, via) => {
    editingRef.current = key;
    lastRef.current = key;
    setEditing({ key, via });
  };

  // An answer the keys reached is selected, as the browser's own Tab would, so typing replaces it (D-205).
  useEffect(() => {
    if (editing.key !== null && editing.via === 'keys') document.activeElement?.select?.();
  }, [editing]);

  // Close the open answer and drop its draft. The ref goes first, so the blur of an editor on its way out saves nothing.
  const close = (key) => {
    editingRef.current = null;
    setEditing((now) => (now.key === key ? { key: null, via: 'click' } : now));
    setDrafts((now) => {
      const next = { ...now };
      delete next[key];
      return next;
    });
  };

  const draftFor = (row) => drafts[row.key] ?? draftOf(row.value);

  /** Save what the editor holds; resolves to the fresh payload with `reload` (null when nothing was saved). */
  const commit = (row, text, { reload = false } = {}) => {
    close(row.key);
    const value = String(text ?? '').trim();
    // An unchanged answer writes nothing, unless a refused save's sentence is showing: then it goes, and clears it.
    if (sameAnswer(value, row.value) && !writes.errorOf(row.key)) return Promise.resolve(null);
    const saved = writes.save(row.key, value, row.value);
    return reload ? saved : Promise.resolve(null);
  };

  const onEditorKey = (event, row) => {
    if (event.nativeEvent?.isComposing) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      close(row.key);
      return;
    }
    if (event.key !== 'Enter' && event.key !== 'Tab') {
      // A select or date the mouse opened, now driven by the keys, holds its pick like one the keys reached.
      if (editing.via === 'click' && HOLDS.includes(row.question.type)) setEditing({ key: row.key, via: 'keys' });
      return;
    }
    event.preventDefault();
    const text = draftFor(row);
    const how = { required: event.key === 'Tab', back: event.shiftKey };
    const changed = !sameAnswer(text, row.value);
    if (changed && revealsOthers(formMeta, row.key)) {
      commit(row, text, { reload: true }).then((fresh) => {
        if (editingRef.current !== null) return; // a click opened another answer meanwhile
        const after = fresh ? buildSections(formMeta, fresh) : sections;
        open((nextRow(after, row.key, how) || row).key, 'keys');
      });
      return;
    }
    const next = nextRow(sections, row.key, how);
    commit(row, text);
    open((next || row).key, 'keys');
  };

  useIntakeKeys({
    rootRef,
    enabled: enabled && Boolean(data),
    onKey: (key, back, target) => {
      const rowEl = target.closest?.('[data-intake-field]');
      const from = rowEl ? rowEl.dataset.intakeField : lastRef.current;
      const next = nextRow(sections, from, { required: key === 'Tab', back });
      if (next) open(next.key, 'keys');
    },
  });

  /** What one row needs to draw and edit itself. */
  const rowProps = (row) => {
    const isEditing = editing.key === row.key;
    const keyed = isEditing && editing.via === 'keys';
    const saveOnPick = INSTANT.includes(row.question.type) && row.question.type !== 'multi' && !keyed;
    return {
      row,
      editing: isEditing,
      draft: draftFor(row),
      error: writes.errorOf(row.key),
      onOpen: () => open(row.key, 'click'),
      onKeyDown: (event) => onEditorKey(event, row),
      onChange: (text) => {
        setDrafts((now) => ({ ...now, [row.key]: text }));
        if (saveOnPick) commit(row, text);
      },
      // Only the answer still open saves: one Enter, Tab or Escape already closed never saves twice on its blur.
      onBlur: saveOnPick ? undefined : () => editingRef.current === row.key && commit(row, draftFor(row)),
      onDone: () => editingRef.current === row.key && commit(row, draftFor(row)),
    };
  };

  return { sections, rowProps, editingKey: editing.key };
}
