import { useEffect, useRef, useState } from 'react';
import { previewSplit, useSaveSplit } from '../../api/commission';
import { errorStatus, errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { complete, draftFrom, rowsFor } from './splitModel';

const DEBOUNCE_MS = 350; // the old live preview's wait (H18)

/**
 * The split editor's state (H18–H20): the draft, whether it was touched, the live preview (debounced, never stored;
 * the body carries the basis the GET returned, so the server does not work the line states out again), the errors
 * keyed as the server keys them, the scope, Save and Discard. The editor is keyed by the saved split, so a save or a
 * refetch that changes it starts a fresh draft.
 */
export default function useSplitDraft({ target, split, basis, preview }) {
  const toast = useToast();
  const save = useSaveSplit(target);
  const [draft, setDraft] = useState(() => draftFrom(split));
  const [dirty, setDirty] = useState(false);
  const [errors, setErrors] = useState({});
  const [live, setLive] = useState(null);
  const [scope, setScope] = useState(split.scope);
  const asked = useRef(0);

  useEffect(() => {
    if (!dirty || !complete(draft)) return undefined;
    const timer = setTimeout(async () => {
      const ticket = ++asked.current;
      try {
        const data = await previewSplit(target, rowsFor(draft), basis);
        if (ticket !== asked.current) return;
        setLive(data.preview);
        setErrors({});
      } catch (error) {
        if (ticket !== asked.current) return;
        if (errorStatus(error) === 400) setErrors(error.response.data || {});
      }
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [draft, dirty, target, basis]);

  // `quiet`: a change of what is open, not of the split (the terms toggle), keeps the draft untouched.
  function change(next, { quiet = false } = {}) {
    setDraft(next);
    if (!quiet) setDirty(true);
  }

  function discard() {
    asked.current += 1;
    setDraft(draftFrom(split));
    setDirty(false);
    setErrors({});
    setLive(null);
  }

  function submit() {
    setErrors({});
    save.mutate(
      { scope, rows: rowsFor(draft) },
      {
        onSuccess: () => {
          setDirty(false);
          setLive(null);
        },
        onError: (error) => {
          if (errorStatus(error) === 400) {
            setErrors(error.response.data || {});
            toast.error('Check the highlighted rows.');
          } else toast.error(errorText(error));
        },
      },
    );
  }

  return {
    draft,
    dirty,
    errors,
    scope,
    setScope: (next) => {
      setScope(next);
      setDirty(true);
    },
    change,
    discard,
    submit,
    saving: save.isPending,
    preview: dirty && live ? live : preview,
  };
}
