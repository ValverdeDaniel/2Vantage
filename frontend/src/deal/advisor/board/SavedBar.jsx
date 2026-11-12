import { useState } from 'react';
import { useDeleteView, useSaveView, useSavedViews } from '../../../api/savedViews';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import SavedSetupDialog from './SavedSetupDialog';

/*
 * Saved setups, Mine and Shared (plan.md §8.14; F28, OQ7; the old SavedFilterBar.jsx): "the analysis I always run",
 * named and reusable across deals. The select offers this person's setups, then the team's shared ones, pinned to
 * this line or to any line. Applying one sets the whole board (filters, columns, sort, layout) and never switches the
 * line; "— none —" (and deleting the one applied) is back to an unfiltered board. ＋ Save current stores the board as it is; Update and Delete show for the owner or an admin. Switching line
 * drops the pick, so the select never names a setup that is not offered here.
 */
export default function SavedBar({ view = 'quotes', line, lineLabel, current, onApply }) {
  const toast = useToast();
  const sets = useSavedViews(view, line);
  const save = useSaveView();
  const remove = useDeleteView();
  const [picked, setPicked] = useState({ line, id: '' });
  const [form, setForm] = useState(null); // null = closed
  const activeId = picked.line === line ? picked.id : '';
  const list = sets.data ?? [];
  const active = list.find((set) => String(set.id) === activeId) ?? null;
  const mine = list.filter((set) => set.is_mine);
  const theirs = list.filter((set) => !set.is_mine);

  const apply = (id) => {
    setPicked({ line, id });
    const found = list.find((set) => String(set.id) === id);
    onApply(found ? found.config : {}); // "— none —" is back to an unfiltered board, as in the old bar
  };
  const open = (existing) =>
    setForm({
      key: Date.now(),
      id: existing?.id ?? null,
      name: existing?.name ?? '',
      description: existing?.description ?? '',
      lineKey: line,
      line: existing ? existing.line : line,
      shared: existing?.shared ?? false,
      errors: {},
    });
  const submit = async (draft) => {
    const body = { name: draft.name, description: draft.description, view, line: draft.line, shared: draft.shared, config: current };
    try {
      const saved = await save.mutateAsync(draft.id ? { id: draft.id, ...body } : body);
      setPicked({ line, id: String(saved.id) });
      setForm(null);
      toast.success(draft.id ? `“${saved.name}” updated` : `“${saved.name}” saved`);
    } catch (error) {
      const data = error?.response?.status === 400 ? error.response.data : null;
      if (data && typeof data === 'object' && !data.detail) setForm({ ...draft, errors: data });
      else toast.error(errorText(error));
    }
  };
  const del = async () => {
    try {
      await remove.mutateAsync(active.id);
      setPicked({ line, id: '' });
      onApply({});
      toast.success(`“${active.name}” deleted`);
    } catch (error) {
      toast.error(errorText(error));
    }
  };

  return (
    <div className="bnf-advisor-saved" role="group" aria-label="Saved board setups">
      <span className="bnf-advisor-views-label">Saved</span>
      <select
        className="filter-select bnf-saved-pick"
        aria-label="Saved setups"
        value={activeId}
        onChange={(event) => apply(event.target.value)}
        title="A named setup — the filters, the columns and the sort, together"
      >
        <option value="">— none —</option>
        {mine.length > 0 && (
          <optgroup label="Mine">
            {mine.map((set) => (
              <option key={set.id} value={String(set.id)}>
                {set.name}
                {set.shared ? ' · shared' : ''}
              </option>
            ))}
          </optgroup>
        )}
        {theirs.length > 0 && (
          <optgroup label="Shared by the team">
            {theirs.map((set) => (
              <option key={set.id} value={String(set.id)}>
                {set.name} · {set.owner_name}
              </option>
            ))}
          </optgroup>
        )}
      </select>
      <button type="button" className="btn btn-secondary btn-sm" onClick={() => open(null)} title="Save the current quote comparison setup under a name">
        ＋ Save current
      </button>
      {active?.can_edit && (
        <>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={save.isPending}
            onClick={() => open(active)}
            title="Overwrite this set with what is on screen now"
          >
            Update
          </button>
          <button type="button" className="btn btn-secondary btn-sm" disabled={remove.isPending} onClick={del}>
            Delete
          </button>
        </>
      )}
      {active?.description && <span className="bnf-saved-note">{active.description}</span>}
      {active && !active.can_edit && <span className="bnf-saved-note">{active.owner_name}’s — “Save current” to make your own copy</span>}
      {form && (
        <SavedSetupDialog key={form.key} form={form} lineLabel={lineLabel} busy={save.isPending} onClose={() => setForm(null)} onSubmit={submit} />
      )}
    </div>
  );
}
