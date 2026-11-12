import { useCallback, useEffect, useRef, useState } from 'react';
import { useAddRow, useRemoveRow, useSaveAnswers } from '../../api/questionnaire';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { fieldOf, withoutSaved } from './formModel';

const TEXT_WAIT = 700; // typed text saves 700 ms after the last key; pickers save at once (G40)
const AT_ONCE = new Set(['choice', 'yesno', 'date']);
const REASONS = {
  not_number: 'is not a number',
  not_offered: 'is not one of the choices',
  too_long: 'is too long',
  unknown: 'is not on this form',
  unknown_row: 'is on a row that is gone',
};

/*
 * The form's typing (G40): a draft of what is typed, saved through one serial mutation scope per form, text after a
 * pause and pickers at once. A save that lands clears only the draft keys it carried that still say the same, so
 * typing during a save survives (`withoutSaved`). Every answer the server dropped is named in a toast (G88's fix).
 * `flush()` sends what waits now and resolves when it lands (Enter and Tab on a driver wait for it, G25).
 */
export default function useAnswerDraft(deal, form, spec) {
  const toast = useToast();
  const save = useSaveAnswers(deal.id, form);
  const { mutateAsync: saveAnswers } = save; // stable, unlike the result object: the inputs' handlers stay the same
  const { mutate: addRow } = useAddRow(deal.id, form);
  const { mutate: removeRow } = useRemoveRow(deal.id, form);
  const [draft, setDraft] = useState({});
  const pending = useRef({});
  const timer = useRef(null);

  const flush = useCallback(() => {
    clearTimeout(timer.current);
    const sent = pending.current;
    pending.current = {};
    if (!Object.keys(sent).length) return Promise.resolve(null);
    return saveAnswers({ answers: sent })
      .then((answer) => {
        setDraft((current) => withoutSaved(current, sent));
        const dropped = answer.dropped || [];
        if (dropped.length && spec) {
          const words = dropped.map((d) => `${fieldOf(spec, d.slot)?.label || d.slot} ${REASONS[d.reason] || ''}`);
          toast.error(`Not saved: ${words.join('; ')}.`);
        }
        return answer;
      })
      .catch((error) => {
        toast.error(errorText(error, { fallback: 'Could not save the answers.' }));
        return null;
      });
  }, [saveAnswers, spec, toast]);

  const change = useCallback(
    (slot, value) => {
      setDraft((current) => ({ ...current, [slot]: value }));
      pending.current = { ...pending.current, [slot]: value };
      clearTimeout(timer.current);
      const type = spec ? fieldOf(spec, slot)?.type : 'text';
      if (AT_ONCE.has(type)) flush();
      else timer.current = setTimeout(flush, TEXT_WAIT);
    },
    [flush, spec],
  );

  // Leaving the form (a chip, another tab) sends what waits first.
  const flushRef = useRef(flush);
  useEffect(() => {
    flushRef.current = flush;
  }, [flush]);
  useEffect(() => () => flushRef.current(), []);

  const onAddRow = useCallback(
    async (block) => {
      await flush();
      addRow(block, { onError: (error) => toast.error(errorText(error, { fallback: 'Could not add a row.' })) });
    },
    [addRow, flush, toast],
  );

  const onRemoveRow = useCallback(
    async (block, rowId) => {
      await flush();
      removeRow(
        { block, rowId },
        { onError: (error) => toast.error(errorText(error, { fallback: 'Could not remove the row.' })) },
      );
    },
    [removeRow, flush, toast],
  );

  return { draft, change, flush, onAddRow, onRemoveRow, saving: save.isPending };
}
