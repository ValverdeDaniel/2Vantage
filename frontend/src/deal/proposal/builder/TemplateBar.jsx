import { useState } from 'react';
import { useDeleteTemplate, useSaveTemplate, useTemplates } from '../../../api/proposalTemplates';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import TemplateDialog from './TemplateDialog';

/*
 * A TEMPLATE bar (plan.md §8.14; J68, OQ7; the old TemplateBar.jsx at 891f1b3, same words and classes): a part of
 * the proposal — how the documents look (`layout`), a line's rows (`rows`) or the executive summary (`summary`) —
 * saved under a name and reused on the next client. The select offers the built-in ones, then Mine, then the team's
 * shared ones, those pinned to this line or to any line. Applying one writes this deal (`onApply`, one PATCH); it
 * never binds the deal, so a template edited later changes no proposal. A built-in one reads as chosen while the deal
 * still matches it (`matches`); "— none —" leaves the deal as it is. Update and Delete show for the owner or an admin.
 */
export default function TemplateBar({ kind, kindLabel, line = '', lineLabel = '', current, matches, placeholders, busy, onApply }) {
  const toast = useToast();
  const list = useTemplates(kind, line).data ?? [];
  const save = useSaveTemplate();
  const remove = useDeleteTemplate();
  const [picked, setPicked] = useState({ line, id: '' });
  const [form, setForm] = useState(null);
  const builtIn = list.filter((template) => template.built_in);
  const mine = list.filter((template) => template.is_mine);
  const theirs = list.filter((template) => !template.is_mine && !template.built_in);
  const chosenId = picked.line === line ? picked.id : '';
  const shownId = chosenId || builtIn.find((template) => matches?.(template.config))?.id || '';
  const active = list.find((template) => String(template.id) === String(shownId)) ?? null;

  const apply = (id) => {
    const found = list.find((template) => String(template.id) === id);
    setPicked({ line, id: found?.built_in ? '' : id });
    if (found) onApply(found.config);
  };
  const open = (existing) =>
    setForm({
      key: Date.now(),
      id: existing?.id ?? null,
      name: existing?.name ?? '',
      description: existing?.description ?? '',
      lineKey: line,
      line: existing ? existing.line : '',
      shared: existing?.shared ?? false,
      errors: {},
    });
  const submit = async (draft) => {
    const body = { name: draft.name, description: draft.description, kind, line: draft.line, shared: draft.shared, config: current };
    try {
      const saved = await save.mutateAsync(draft.id ? { id: draft.id, ...body } : body);
      setPicked({ line, id: String(saved.id) });
      setForm(null);
      toast.success(draft.id ? `“${saved.name}” updated` : `“${saved.name}” saved`);
    } catch (error) {
      const data = error?.response?.status === 400 ? error.response.data : null;
      if (data && typeof data === 'object' && !data.detail) setForm({ ...draft, errors: data });
      else toast.error(errorText(error, { fallback: 'Could not save this template' }));
    }
  };
  const del = async () => {
    try {
      await remove.mutateAsync(active.id);
      setPicked({ line, id: '' });
      toast.success(`“${active.name}” deleted`);
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not delete this template' }));
    }
  };

  const options = (rows, words) => rows.map((t) => <option key={t.id} value={String(t.id)}>{words(t)}</option>);
  return (
    <div className="bnf-advisor-saved" role="group" aria-label={`${kindLabel} templates`}>
      <span className="bnf-advisor-views-label">Template</span>
      <select
        className="filter-select bnf-saved-pick"
        aria-label={`${kindLabel} template`}
        value={String(shownId)}
        disabled={busy}
        onChange={(event) => apply(event.target.value)}
        title={`A saved ${kindLabel.toLowerCase()} — applying it fills this deal in`}
      >
        <option value="">— none —</option>
        {builtIn.length > 0 && <optgroup label="Built in">{options(builtIn, (t) => t.name)}</optgroup>}
        {mine.length > 0 && <optgroup label="Mine">{options(mine, (t) => `${t.name}${t.shared ? ' · shared' : ''}`)}</optgroup>}
        {theirs.length > 0 && <optgroup label="Shared by the team">{options(theirs, (t) => `${t.name} · ${t.owner_name}`)}</optgroup>}
      </select>
      <button type="button" className="btn btn-secondary btn-sm" onClick={() => open(null)} title={`Save this ${kindLabel.toLowerCase()} to reuse on the next client`}>
        ＋ Save as template
      </button>
      {active?.can_edit && (
        <>
          <button type="button" className="btn btn-secondary btn-sm" disabled={save.isPending} onClick={() => open(active)} title="Overwrite this template with what is on screen now">
            Update
          </button>
          <button type="button" className="btn btn-secondary btn-sm" disabled={remove.isPending} onClick={del}>
            Delete
          </button>
        </>
      )}
      {active?.description && <span className="bnf-saved-note">{active.description}</span>}
      {active && !active.can_edit && !active.built_in && (
        <span className="bnf-saved-note">{active.owner_name}’s — “Save as template” to make your own copy</span>
      )}
      {form && (
        <TemplateDialog
          key={form.key}
          form={form}
          kindLabel={kindLabel}
          lineLabel={lineLabel}
          placeholders={placeholders}
          busy={save.isPending}
          onClose={() => setForm(null)}
          onSubmit={submit}
        />
      )}
    </div>
  );
}
