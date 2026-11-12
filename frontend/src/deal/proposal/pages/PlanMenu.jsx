import { useState } from 'react';

/*
 * ⋯ More under a column's head in the builder (plan.md §8.14; J14, J50; the old ProposalPlansCard.jsx `menuFor` at
 * 891f1b3): "Name on client documents", what the client files call the plan instead of its code. Saved on blur or
 * Enter through quotes' PATCH; Esc leaves it. "One column with…" joins this menu with the pair fold (J15, slice 33).
 */
export default function PlanMenu({ plan, busy, onRename }) {
  const [naming, setNaming] = useState(false);
  if (plan.kind === 'current') return null;
  return (
    <details className="bnf-pg-menu">
      <summary title="The client's name for this plan">⋯ More</summary>
      <div className="bnf-pg-menu-body">
        {naming ? (
          <input
            className="bnf-build-option-client"
            autoFocus
            type="text"
            maxLength={200}
            defaultValue={plan.client_name || ''}
            placeholder="Name on client documents"
            aria-label={`What client documents call ${plan.name}`}
            onBlur={(event) => {
              const name = event.target.value.trim();
              setNaming(false);
              if (name !== (plan.client_name || '')) onRename(plan, name);
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter') event.target.blur();
              if (event.key === 'Escape') setNaming(false);
            }}
          />
        ) : (
          <button
            type="button"
            className="bnf-override-link"
            title="What client documents call this plan"
            disabled={busy}
            onClick={() => setNaming(true)}
          >
            {plan.client_name ? `“${plan.client_name}” ✎` : '✎ Name on client documents'}
          </button>
        )}
      </div>
    </details>
  );
}
