import { useCallback } from 'react';
import { fieldOf, nextSlot } from './formModel';

/*
 * Enter and Tab on either layout (G41; D-204, D-205): Enter goes to the very next question, Tab to the next blank
 * required one; both wrap, Shift goes back, never to a button, and nothing happens on a locked form. The answer left
 * behind saves at once. On a driver — a question others hang on — the move waits for the save's reply, so a question
 * it reveals is next (G25). A filled answer reached is selected, as the browser's own Tab would.
 */
export default function useFormKeys({ paperRef, spec, data, draft, flush, locked }) {
  const focus = useCallback(
    (slot) => {
      const input = paperRef.current?.querySelector(`[data-q-slot="${CSS.escape(slot)}"] :is(input, select, textarea)`);
      input?.focus({ preventScroll: true });
      input?.select?.();
      input?.scrollIntoView?.({ block: 'center' });
    },
    [paperRef],
  );

  return useCallback(
    async (event) => {
      if (locked || event.nativeEvent.isComposing || (event.key !== 'Enter' && event.key !== 'Tab')) return;
      if (event.target.tagName === 'TEXTAREA' && event.key === 'Enter') return;
      const from = event.target.closest?.('[data-q-slot]')?.getAttribute('data-q-slot');
      if (!from) return;
      event.preventDefault();
      const options = { required: event.key === 'Tab', back: event.shiftKey };
      const typed = new Set(Object.keys(draft).filter((slot) => String(draft[slot]).trim()));
      const driver = Boolean(fieldOf(spec, from)?.driver);
      const saving = flush();
      const fresh = driver ? (await saving) || data : data;
      const blanks = (fresh.blanks || []).filter((slot) => !typed.has(slot) || slot === from);
      const next = nextSlot(fresh.order || [], blanks, from, options);
      if (next) focus(next);
    },
    [data, draft, flush, focus, locked, spec],
  );
}
