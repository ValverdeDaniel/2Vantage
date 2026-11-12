import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { intakeKey, patchAnswers, useIntake } from '../../api/intake';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import RankButton from './RankButton';

/*
 * Client guidance in the drawer (plan.md §8.17, §4.5 †; D6, D98, F111; the old WorkWithClaude `bnf-wwc-guidance`): what
 * the client wants — budget, networks, lines, deductible or benefit levels — which Claude reads in every turn and Rank
 * reads: ⚖ Rank plans sits here (slice 37, `RankButton`). It is intake's `client_guidance` answer: ✎ Edit saves it
 * through `PATCH deals/{id}/intake/` with the text the person saw (a 409 says it changed meanwhile), and Claude's
 * `update_client_guidance` changes it through the same writer. Never on a client file. Open or closed per click.
 */
export default function GuidanceBox({ dealId, state, model }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const intake = useIntake(dealId);
  const [open, setOpen] = useState(true);
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const guidance = intake.data?.answers?.client_guidance || '';

  async function save() {
    setSaving(true);
    try {
      await patchAnswers(dealId, { answers: { client_guidance: draft }, expect: { client_guidance: guidance } });
      await queryClient.invalidateQueries({ queryKey: intakeKey(dealId) });
      setDraft(null);
    } catch (error) {
      toast.error(errorText(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bnf-wwc-guidance">
      <button type="button" className="bnf-wwc-guidance-head" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="bnf-guidance-label">Client guidance</span>
        <span className="bnf-wwc-caret">{open ? '▾' : '▸'}</span>
      </button>
      {open && draft === null && (
        <>
          <div className={`bnf-guidance-text ${guidance ? '' : 'bb-empty'}`}>
            {guidance ||
              'None yet — tell Claude below what the client wants: budget, networks, which lines, deductible or benefit levels.'}
          </div>
          <div className="bnf-wwc-guidance-actions">
            <RankButton dealId={dealId} guidance={guidance} state={state} model={model} />
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setDraft(guidance)}>
              ✎ Edit
            </button>
          </div>
        </>
      )}
      {open && draft !== null && (
        <>
          <textarea
            rows={4}
            value={draft}
            maxLength={4000}
            aria-label="Client guidance"
            onChange={(event) => setDraft(event.target.value)}
          />
          <div className="bnf-wwc-guidance-actions">
            <button type="button" className="btn btn-primary btn-sm" disabled={saving} onClick={save}>
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button type="button" className="btn btn-secondary btn-sm" disabled={saving} onClick={() => setDraft(null)}>
              Cancel
            </button>
          </div>
        </>
      )}
    </div>
  );
}
