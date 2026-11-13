import { useCallback, useReducer, useState } from 'react';
import { addPeople, signBor, statusOf, submitAnswers, uploadFile } from './portalApi';
import { answersReducer, initialAnswers, pendingAnswers, savedWords } from './portalModel';
import { opensOnReceipt } from './receiptModel';
import useAutosave from './useAutosave';
import useFormWrites from './useFormWrites';

/*
 * Everything the portal page writes (plan.md §7.14, §8.20; L90, L93–L98): the answers with their autosave, the files
 * staged until Save or Submit (one request each, L97), the BOR's typed name (it rides Save or Submit too), people
 * added at once, and Submit. A refusal is said where it belongs; nothing typed is ever wiped (old D-208). The
 * questionnaires (slice 58, `useFormWrites`): their answers ride the same autosave, each save answering the forms'
 * fresh states; their rows go at once; the officer's signature rides Save or Submit after the answers, and a
 * signature blank answers hold stops Submit until "Sign anyway". After Submit (slice 59) the page shows the receipt the
 * answer carried; a submitted link opens on it again unless a follow-up waits for an answer; `back` returns to the form.
 *
 * Returns {answers, bind, staged, stage, unstage, borName, setBorName, note, problem, setProblem, busy, submitted,
 * receipt, back, save, submit, addPerson, confirming, forms}.
 */
export default function usePortalWrites({ token, page, writes, onReload, onChallenge }) {
  const [answers, dispatch] = useReducer(answersReducer, page, initialAnswers);
  const [seededFrom, setSeededFrom] = useState(page);
  const [staged, setStaged] = useState({});
  const [borName, setBorName] = useState('');
  const [note, setNote] = useState('');
  const [problem, setProblem] = useState('');
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(() => opensOnReceipt(page));
  const [receipt, setReceipt] = useState(page.receipt || null);
  const [confirming, setConfirming] = useState(false);

  // A fresh payload (after files, people or a poll) takes its values and bases, keeping what was typed and not taken.
  if (seededFrom !== page) {
    setSeededFrom(page);
    dispatch({ type: 'reseed', page });
    if (page.receipt) setReceipt(page.receipt);
  }

  const challenge = useCallback(() => onChallenge(), [onChallenge]);
  const forms = useFormWrites({ token, page, dispatch, onProblem: setProblem });
  const { adopt } = forms;
  const onSaved = useCallback((answer) => adopt(answer?.questionnaires), [adopt]);
  const { flush } = useAutosave({
    token,
    answers,
    dispatch,
    enabled: writes && !busy && !submitted,
    onNote: setNote,
    onProblem: setProblem,
    onChallenge: challenge,
    onSaved,
  });

  const set = useCallback((ref, value) => {
    dispatch({ type: 'set', ref, value });
    setConfirming(false);
  }, []);
  const bind = {
    values: answers.values,
    conflicts: answers.conflicts,
    errors: answers.errors,
    set,
    keepTheirs: (ref) => dispatch({ type: 'keepTheirs', ref }),
    useMine: (ref) => dispatch({ type: 'useMine', ref }),
    readOnly: !writes,
  };

  const stage = (slot, files) => {
    setStaged((current) => ({ ...current, [slot]: [...(current[slot] || []), ...files] }));
    setConfirming(false);
  };
  const unstage = (slot, file) =>
    setStaged((current) => {
      const left = (current[slot] || []).filter((one) => one !== file);
      const next = { ...current };
      if (left.length) next[slot] = left;
      else delete next[slot];
      return next;
    });

  // Each staged file in its own request; each leaves the list as it lands, so Try again sends only the rest.
  async function sendFiles() {
    let sent = 0;
    for (const [slot, files] of Object.entries(staged)) {
      for (const file of files) {
        await uploadFile(token, slot, file);
        unstage(slot, file);
        sent += 1;
      }
    }
    return sent;
  }

  async function sendBor() {
    const name = borName.trim();
    if (!name || page.intake?.blocks?.bor?.signed) return false;
    await signBor(token, name);
    setBorName('');
    return true;
  }

  function said(error, doing) {
    const code = statusOf(error);
    const body = error?.response?.data || {};
    if (code === 428) return onChallenge();
    if (code === 409 && body.conflicts) {
      dispatch({ type: 'conflicts', list: body.conflicts });
      return setProblem('Someone at your company changed some answers while you had this page open — see below.');
    }
    if (code === 400 && body.answers) {
      dispatch({ type: 'refused', errors: body.answers });
      return setProblem(Object.values(body.answers).join(' '));
    }
    const first = body.detail || Object.values(body).flat().find((text) => typeof text === 'string');
    return setProblem(first || `Something went wrong ${doing} — everything you typed is still here. Please try again.`);
  }

  async function save() {
    setBusy(true);
    setNote('');
    setProblem('');
    try {
      const files = await sendFiles();
      const signed = await sendBor();
      await flush();
      const signing = await forms.signAll();
      setNote(savedWords('Progress saved'));
      if (signing.held) setProblem(HELD);
      if (files || signed || signing.signed) onReload();
    } catch (error) {
      if (!error?.response?.data?.conflicts && statusOf(error) !== 400) said(error, 'saving');
    }
    setBusy(false);
  }

  async function submit(openItems) {
    if (openItems > 0 && !confirming) {
      setConfirming(true);
      return;
    }
    setBusy(true);
    setProblem('');
    try {
      await sendFiles();
      await sendBor();
      await flush();
      if ((await forms.signAll()).held) {
        setProblem(HELD);
        setConfirming(false);
        setBusy(false);
        return;
      }
      const done = await submitAnswers(token, pendingAnswers(answers));
      setReceipt(done?.receipt || null);
      setSubmitted(true);
    } catch (error) {
      said(error, 'submitting');
    }
    setConfirming(false);
    setBusy(false);
  }

  async function addPerson(person) {
    try {
      await addPeople(token, [person]);
    } catch (error) {
      const body = error?.response?.data || {};
      throw new Error(body.detail || (body.people || [])[0] || 'Could not add that person — please try again.');
    }
    onReload();
  }

  return {
    answers,
    bind,
    staged,
    stage,
    unstage,
    borName,
    setBorName,
    note,
    problem,
    setProblem,
    busy,
    submitted,
    receipt,
    back: () => setSubmitted(false),
    confirming,
    save,
    submit,
    addPerson,
    forms,
  };
}

const HELD = 'A questionnaire is not signed yet: some required answers are still blank — see the form.';
