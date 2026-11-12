import { useState } from 'react';
import { useDealAiSettings } from '../../api/chats';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';

/*
 * The deal's AI budget, set by an admin in the drawer's head bar (plan.md §8.17, §10.3; D100, OQ34's default: only
 * admins change it; B16: the old refusal named a field no screen showed). Blank gives back the default
 * (`AI_DEAL_BUDGET_USD`). Everyone else sees the spend line only.
 */
export default function BudgetEdit({ dealId, spend }) {
  const toast = useToast();
  const settings = useDealAiSettings(dealId);
  const [draft, setDraft] = useState(null);

  async function save() {
    try {
      await settings.mutateAsync({ budget_usd: draft.trim() === '' ? null : draft.trim() });
      setDraft(null);
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  if (draft === null) {
    return (
      <button
        type="button"
        className="bnf-linklike"
        title={`Change this deal's Claude budget (${spend?.own_budget ? 'its own' : 'the default'} now)`}
        onClick={() => setDraft(spend?.own_budget ? String(Number(spend.budget_usd)) : '')}
      >
        ✎ Budget
      </button>
    );
  }
  return (
    <span className="bnf-chatbar-pick">
      $
      <input
        value={draft}
        size={6}
        inputMode="decimal"
        aria-label="Deal budget in dollars"
        placeholder="default"
        autoFocus
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') save();
          if (event.key === 'Escape') {
            event.stopPropagation();
            setDraft(null);
          }
        }}
      />
      <button type="button" className="btn btn-primary btn-sm" disabled={settings.isPending} onClick={save}>
        Save
      </button>
    </span>
  );
}
