import { useCallback, useEffect, useRef, useState } from 'react';
import { saveAnswers, statusOf } from './portalApi';
import { pendingAnswers, savedWords, sentValues } from './portalModel';

const FIRST_WAIT = 1500;
const LONGEST_WAIT = 60000;
export const NOT_SAVED_YET =
  'Your latest changes have not saved yet. Everything you typed is still here, and we will keep trying.';

/*
 * Autosave (plan.md §8.20; L95, L96; old `BenefitsClientPortal` D-059/D-062/D-208): 1.5 s after the last change, one
 * save at a time, only what changed since it was last taken, each with its base. A conflict holds its answers for
 * the person (keep theirs or use mine); a refusal says why and waits for their next change; a blip tries again
 * further apart each time, up to a minute. Never on a page that cannot write (a staff session, a preview, a lost deal).
 *
 * answers/dispatch: the answers' reducer (portalModel). onNote(text), onProblem(text), onChallenge(): what the page
 * shows; onSaved(answer): a save that landed (its questionnaires' fresh states, slice 58). Returns {flush}: send what
 * is pending now (Save and Submit call it), resolving to the save's answer or null.
 */
export default function useAutosave({ token, answers, dispatch, enabled, onNote, onProblem, onChallenge, onSaved }) {
  const inFlight = useRef(false);
  const fails = useRef(0);
  const [tick, setTick] = useState(0);
  const pendingKey = JSON.stringify(pendingAnswers(answers));

  const send = useCallback(
    async (pending) => {
      inFlight.current = true;
      try {
        const answer = await saveAnswers(token, pending);
        dispatch({ type: 'saved', sent: sentValues(pending), bases: answer.bases || {} });
        onSaved?.(answer);
        fails.current = 0;
        onProblem('');
        return answer;
      } catch (error) {
        const code = statusOf(error);
        const body = error?.response?.data || {};
        if (code === 428) onChallenge();
        else if (code === 409 && body.conflicts) dispatch({ type: 'conflicts', list: body.conflicts });
        else if (code === 400 && body.answers && typeof body.answers === 'object') {
          dispatch({ type: 'refused', errors: body.answers });
          onProblem(Object.values(body.answers).join(' '));
        } else if (code && code >= 400 && code < 500 && code !== 429) onProblem(body.detail || NOT_SAVED_YET);
        else {
          fails.current += 1;
          onProblem(NOT_SAVED_YET);
        }
        throw error;
      } finally {
        inFlight.current = false;
        setTick((n) => n + 1);
      }
    },
    [token, dispatch, onProblem, onChallenge, onSaved],
  );

  useEffect(() => {
    if (!enabled || pendingKey === '{}') return undefined;
    const wait = Math.min(FIRST_WAIT * 2 ** fails.current, LONGEST_WAIT);
    const timer = setTimeout(() => {
      if (inFlight.current) return; // the save in flight re-arms this when it lands
      send(JSON.parse(pendingKey)).then(
        () => onNote(savedWords('Saved automatically')),
        () => onNote(''),
      );
    }, wait);
    return () => clearTimeout(timer);
  }, [pendingKey, enabled, tick, send, onNote]);

  const flush = useCallback(async () => {
    if (pendingKey === '{}') return null;
    return send(JSON.parse(pendingKey));
  }, [pendingKey, send]);

  return { flush };
}
