import { useRef, useState } from 'react';
import { useMeta } from '../../../api/meta';
import { useCensusBlanks, useEnter } from '../../../api/reviewForm';
import { errorText } from '../../../lib/errors';
import CellInput from '../../../portal/CellInput';
import { useToast } from '../../../ui/useToast';
import FieldInput from '../../shared/FieldInput';
import FromClientToggle from '../../shared/FromClientToggle';
import { censusBoxes, intakeBoxes, nextBox, originWords, toSave } from './editModel';

/*
 * Edit mode on the request page (plan.md §8.8; L34, L35; old 891f1b3 `RequestPage.jsx` edit mode): our rows for answers
 * read over the phone. Each box saves when Enter or Tab leaves it (Enter goes to the next box, Tab to the next required
 * blank; Esc undoes the box), one at a time, through the owners' typed writes (`POST review/enter/`); then the page reads
 * once. "These came from the client" (on by default here) saves them as the client's, entered by you (origin relay);
 * off, as typed by you. The census lists each person's blanks (at most 500). Questions only: a block or a file is not
 * typed here.
 */
export default function EditMode({ deal, pane, page, onDone }) {
  const form = useMeta().data?.intake?.form; // the questions' types and options (/api/meta/ `intake.form`, rule 1)
  const [relay, setRelay] = useState(true);
  const [requiredOnly, setRequiredOnly] = useState(false);
  const [drafts, setDrafts] = useState({});
  const [saved, setSaved] = useState({});
  const boxesRef = useRef({});
  const flying = useRef(new Set());
  const enter = useEnter(deal.id);
  const toast = useToast();
  const blanks = useCensusBlanks(deal.id, requiredOnly, pane === 'census');
  const questions = Object.fromEntries((form?.sections || []).flatMap((section) => section.questions.map((q) => [q.key, q])));
  const boxes = pane === 'census' ? censusBoxes(blanks.data) : intakeBoxes(page.items);

  const focus = (ref) => boxesRef.current[ref]?.querySelector('input, select, textarea')?.focus();
  const save = async (ref) => {
    const value = toSave(drafts[ref], saved[ref]);
    if (value === null || flying.current.has(`${ref}=${value}`)) return;
    flying.current.add(`${ref}=${value}`);
    try {
      const answer = await enter.mutateAsync({ answers: { [ref]: value }, origin: relay ? 'relay' : 'typed' });
      setSaved((now) => ({ ...now, [ref]: value }));
      if (!answer.saved.length) toast.success('Already on file: nothing changed');
    } catch (error) {
      toast.error(errorText(error));
    } finally {
      flying.current.delete(`${ref}=${value}`);
    }
  };
  const keys = (ref) => (event) => {
    if (event.key === 'Escape') {
      setDrafts((now) => ({ ...now, [ref]: saved[ref] || '' }));
    } else if (event.key === 'Enter' || event.key === 'Tab') {
      event.preventDefault();
      save(ref);
      const next = nextBox(boxes, ref, event.key === 'Tab');
      if (next) focus(next);
    }
  };
  const box = (ref, input, label, held, required) => (
    <div key={ref} ref={(el) => (boxesRef.current[ref] = el)} className={`rr-fr${saved[ref] ? ' rr-fr-chip-saved' : ''}`}
      onKeyDown={keys(ref)} onBlur={() => save(ref)}>
      <div className="rr-fr-label">
        {label}
        {required && <span className="rr-fr-req"> *</span>}
      </div>
      <div className="rr-fr-value">{input}</div>
      <div className="rr-fr-status rr-edit-note">{saved[ref] ? 'Saved ✓' : held ? `On file: ${held}` : ''}</div>
    </div>
  );
  const draft = (ref) => (text) => setDrafts((now) => ({ ...now, [ref]: text }));

  return (
    <div className="rr-entry rr-form-editing" aria-label="Edit mode">
      <div className="rr-reqpage-colhead">
        <b>Edit mode</b>
        <span className="rr-edit-note"> · {originWords(relay)}. Enter: next box · Tab: next required blank · Esc: undo the box</span>
        <span className="rr-entry-keys">
          <FromClientToggle checked={relay} onChange={setRelay} />
          <button type="button" className="btn btn-sm btn-secondary" onClick={onDone}>
            Done
          </button>
        </span>
      </div>
      {pane === 'intake' &&
        page.items
          .filter((item) => item.ref.startsWith('intake:') && !item.ref.startsWith('intake:block:'))
          .map((item) => {
            const question = questions[item.ref.slice('intake:'.length)];
            if (!question) return null;
            const input = (
              <FieldInput question={question} value={drafts[item.ref] ?? ''} onChange={draft(item.ref)} 
                label={item.label} />
            );
            return box(item.ref, input, item.label, item.value, item.needed);
          })}
      {pane === 'census' && (
        <>
          <label className="bnf-review-check">
            <input type="checkbox" checked={requiredOnly} onChange={(event) => setRequiredOnly(event.target.checked)} />
            Required blanks only
          </label>
          {blanks.data?.truncated && <div className="rr-edit-note">Showing the first {blanks.data.shown} of {blanks.data.total} blanks.</div>}
          {(blanks.data?.people || []).map((person) => (
            <div key={person.id} className="rr-form-group">
              <div className="rr-form-sechead">
                <b>{person.title}</b>
              </div>
              {person.cells.map((cell) =>
                box(cell.ref, <CellInput field={cell} value={drafts[cell.ref] ?? ''} onChange={draft(cell.ref)} />,
                  cell.label, '', cell.required),
              )}
            </div>
          ))}
          {blanks.data && !blanks.data.people.length && <div className="rr-rail-note">No blank census value to type.</div>}
        </>
      )}
      {pane === 'documents' && <div className="rr-rail-note">Files are not typed: upload them on the Documents tab.</div>}
    </div>
  );
}
