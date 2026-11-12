import axios from 'axios';
import { useEffect, useState } from 'react';
import { previewPriced, useCommitPriced, useSetBundling } from '../../../api/priced';
import { useCopyPlan, useFindIndex } from '../../../api/quotes';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import {
  BUNDLE,
  DUPLICATE,
  bundleScopeIds,
  draftBody,
  draftFromVersion,
  familyAllowed,
  familyMeta,
  openDraft,
} from './pricedKinds';

/*
 * The priced-version draft on the board (plan.md §8.14; F76–F83; the old AdvisorTab's draft state). ＋ on a plan opens
 * a live draft under it; ✎ on a version reopens it, locked to its kind; the editor sits in the draft row or, by the
 * person's choice kept per browser, docked above the table (the old "⌸ Editing in the table / above the table").
 * Every change to the draft asks the server for a dry run (`plans/priced/` with dry_run, 300 ms after the last key),
 * whose figures the draft row shows: the browser works out no money. ✓, Enter or Add commits; ✕ or Esc discards. A
 * draft belongs to its line: switching lines leaves it behind.
 */

const MODE_KEY = 'vantage.bnf.advisor.pricedEditor';
const WAIT_MS = 300;

function readMode() {
  try {
    return window.localStorage.getItem(MODE_KEY) === 'strip' ? 'strip' : 'row';
  } catch {
    return 'row';
  }
}

/** The draft row a source plan shows: its values with the draft's changes, and the dry run's figures. */
function draftPlan(original, found, draft) {
  const copy = draft.family === DUPLICATE;
  return {
    ...original,
    id: `draft-${original.id}`,
    sourceId: original.id,
    sourceName: original.name,
    isDraft: true,
    role: 'alternate',
    starred: false,
    sold: false,
    recommended: false,
    cells: {},
    facts: null,
    name: found?.name ?? original.name,
    derived: found?.derived ?? null,
    values: { ...original.values, ...(found?.changes ?? {}) },
    premium: copy
      ? { monthly: null, reason_words: 'worked out once the copy is added' }
      : (found?.premium ?? original.premium),
    change: copy ? null : (found?.change ?? original.change),
    credit: found?.credit ?? null,
  };
}

/**
 * The board's priced-version kit: the draft and its doors, and what the editors read (meta's words, the line's rate
 * keys and field labels, the finder's index of every line's plans for a bundle's quote to sell).
 */
export default function usePricedDraft({ dealId, line, plans, meta, rateBasis, fields, lineLabel }) {
  const toast = useToast();
  const priced = meta.board.priced;
  const index = useFindIndex(dealId).data?.plans;
  const [state, setState] = useState(null);
  const [mode, setMode] = useState(readMode);
  const [answer, setAnswer] = useState({ key: '', drafts: null, warning: '', error: '' });
  const commitDoor = useCommitPriced(dealId);
  const copyDoor = useCopyPlan(dealId);
  const bundlingDoor = useSetBundling(dealId);
  const draft = state?.line === line ? state : null;
  const byId = new Map(plans.map((plan) => [plan.id, plan]));
  const request = draft ? draftBody(draft, priced.words) : null;
  const sources = draft ? draft.planIds.map((id) => byId.get(id)?.values) : [];
  const key =
    draft && request.body && draft.family !== DUPLICATE ? JSON.stringify([draft.editId, request.body, sources]) : '';

  useEffect(() => {
    if (!key) return undefined;
    const [editId, body] = JSON.parse(key);
    const controller = new AbortController();
    const timer = setTimeout(() => {
      previewPriced({ dealId, editId, body, signal: controller.signal })
        .then((data) => setAnswer({ key, drafts: data.drafts, warning: data.warning, error: '' }))
        .catch((error) => {
          if (!axios.isCancel(error)) setAnswer({ key, drafts: null, warning: '', error: errorText(error) });
        });
    }, WAIT_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [dealId, key]);

  const fresh = Boolean(key) && answer.key === key;
  const patch = (next) => setState((now) => (now ? { ...now, ...next } : now));
  const open = (plan) => setState({ ...openDraft(plan, mode === 'strip'), line });
  const edit = (version) => {
    if (!byId.has(version.derived_from)) {
      toast.error('The original this version was priced from is gone — edit its cells directly.');
      return;
    }
    setState({ ...draftFromVersion(version), line });
  };
  const cancel = () => setState(null);
  const setFamily = (family) =>
    setState((now) => {
      if (!now || now.family === family || now.editId) return now;
      const anchor = byId.get(now.anchorId);
      if (anchor && !familyAllowed(family, anchor)) return now;
      const planIds = !anchor ? now.planIds : family === BUNDLE ? bundleScopeIds(plans, anchor) : [anchor.id];
      return { ...now, family, planIds };
    });
  // "Apply to": the anchor moves with the selection, and a new carrier drops the quotes the old one's bundle linked.
  const reselect = (ids) => {
    if (!draft) return;
    const anchorId = ids.includes(draft.anchorId) || !ids.length ? draft.anchorId : ids[0];
    const carrier = byId.get(anchorId)?.carrier ?? draft.carrier;
    const parts =
      carrier === draft.carrier
        ? draft.parts
        : Object.fromEntries(Object.entries(draft.parts).map(([key, part]) => [key, { ...part, plan_id: null }]));
    patch({ planIds: ids, anchorId, carrier, parts });
  };
  const toggleMode = () => {
    const next = mode === 'row' ? 'strip' : 'row';
    setMode(next);
    try {
      window.localStorage.setItem(MODE_KEY, next);
    } catch {
      // a browser without storage keeps the choice for this visit only
    }
    patch({ expanded: next === 'strip' });
  };

  const commit = async () => {
    if (!draft || commitDoor.isPending || copyDoor.isPending) return;
    const { body, error } = draftBody(draft, priced.words);
    if (error) {
      toast.error(error);
      return;
    }
    const family = familyMeta(priced, draft.family).label;
    try {
      if (draft.family === DUPLICATE) {
        await copyDoor.mutateAsync({ planId: draft.planIds[0], name: body.name });
        toast.success('Duplicated, with its rates');
      } else {
        const done = await commitDoor.mutateAsync({ editId: draft.editId, body });
        const count = draft.editId ? 1 : draft.planIds.length;
        toast.success(draft.editId ? `${family} updated` : `${family} added${count > 1 ? ` to ${count} plans` : ''}`);
        if (done.warning) toast.info(done.warning);
      }
      setState(null);
    } catch (failure) {
      toast.error(errorText(failure));
    }
  };

  // The last dry run stays on screen while the next one is on its way; with nothing typed there is none.
  const rateKeys = priced.rate_keys[rateBasis] ?? [];
  const setEach = (key, next) => {
    const each = { ...(draft?.each ?? {}) };
    if (next == null) delete each[key];
    else each[key] = next;
    patch({ each });
  };
  const found = (id) => (key ? ((answer.drafts ?? []).find((d) => d.original_id === id) ?? null) : null);
  return {
    priced,
    plans,
    byId,
    index,
    rateKeys,
    premiumKeys: [...rateKeys, priced.quoted],
    labelOf: (key) => fields[key]?.label ?? key,
    lineLabel,
    draft,
    mode,
    busy: commitDoor.isPending || copyDoor.isPending,
    pending: Boolean(key) && !fresh,
    error: fresh ? answer.error : '',
    warning: fresh ? answer.warning : '',
    preview: (id) => (draft?.planIds.includes(id) ? found(id) : null),
    /** The draft row under source plan `id`, or null when the draft does not price it. */
    rowFor: (id) => (draft?.planIds.includes(id) && byId.has(id) ? draftPlan(byId.get(id), found(id), draft) : null),
    open,
    edit,
    cancel,
    patch,
    setEach,
    setFamily,
    reselect,
    toggleMode,
    commit,
    setBundling: (plan, bundling) =>
      bundlingDoor.mutateAsync({ planId: plan.id, bundling }).catch((failure) => toast.error(errorText(failure))),
  };
}
