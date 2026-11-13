import { useCallback, useState } from 'react';
import { addFormRow, removeFormRow, signForm, statusOf } from './portalApi';
import { formSeeds } from './questionnaireModel';

/*
 * The questionnaires' own writes on the client's page (plan.md §7.14, §8.20; G87, G93, L91; slice 58): each form's
 * latest state (a save, a row, answers it again), the rows their link adds and removes (at once, as people are added),
 * and the officer's typed signature, kept here until Save or Submit sends it (G93: "saved with the request", the BOR's
 * way). Blank required answers hold a signature: the server says how many, and "Sign anyway" sends it again.
 *
 * Returns {states, adopt, addRow, removeRow, names, setName, anyway, setAnyway, holds, signAll, busy}.
 */
export default function useFormWrites({ token, page, dispatch, onProblem }) {
  const [states, setStates] = useState({});
  const [seededFrom, setSeededFrom] = useState(page);
  const [names, setNames] = useState({});
  const [anyway, setAnyways] = useState({});
  const [holds, setHolds] = useState({});
  const [busy, setBusy] = useState('');

  // A fresh payload carries every form's state: what was answered here since is in it.
  if (seededFrom !== page) {
    setSeededFrom(page);
    setStates({});
  }

  const adopt = useCallback(
    (found) => {
      if (!found || !Object.keys(found).length) return;
      setStates((now) => ({ ...now, ...found }));
      const cards = Object.entries(found).map(([form, state]) => ({ form, state }));
      dispatch({ type: 'adopt', ...formSeeds(cards) });
    },
    [dispatch],
  );

  function failed(error, doing) {
    const body = error?.response?.data || {};
    const first = body.detail || Object.values(body).flat().find((text) => typeof text === 'string');
    onProblem(first || `Something went wrong ${doing} — please try again.`);
  }

  async function addRow(form, block) {
    setBusy(form);
    try {
      const answer = await addFormRow(token, form, block);
      adopt({ [form]: answer.state });
    } catch (error) {
      failed(error, 'adding that row');
    }
    setBusy('');
  }

  async function removeRow(form, block, rowId) {
    setBusy(form);
    try {
      const answer = await removeFormRow(token, form, block, rowId);
      adopt({ [form]: answer.state });
    } catch (error) {
      failed(error, 'removing that row');
    }
    setBusy('');
  }

  const setName = (form, name) => {
    setNames((now) => ({ ...now, [form]: name }));
    setHolds((now) => ({ ...now, [form]: undefined }));
  };
  const setAnyway = (form, value) => setAnyways((now) => ({ ...now, [form]: value }));

  /** Send every typed signature: {signed, held}. A hold stays on its form; anything else throws. */
  async function signAll() {
    let signed = 0;
    let held = 0;
    for (const card of page.questionnaires || []) {
      const name = (names[card.form] || '').trim();
      if (!card.sign || !name) continue;
      try {
        await signForm(token, card.form, name, Boolean(anyway[card.form]));
        setNames((now) => ({ ...now, [card.form]: '' }));
        setHolds((now) => ({ ...now, [card.form]: undefined }));
        signed += 1;
      } catch (error) {
        const body = error?.response?.data || {};
        if (statusOf(error) !== 409 || !body.incomplete) throw error;
        setHolds((now) => ({ ...now, [card.form]: body.incomplete }));
        held += 1;
      }
    }
    return { signed, held };
  }

  return { states, adopt, addRow, removeRow, names, setName, anyway, setAnyway, holds, signAll, busy };
}
