import BudgetEdit from './BudgetEdit';
import { lastRunLine, modelLabel, spendLine } from './drawerWords';

/*
 * The bar under the drawer's head (plan.md §8.17; D8, D9, D100; the old chatControls ChatBar's model row): the one
 * model picker — "Default (Sonnet 5.5)", Sonnet 5.5, and Opus 5.5 for admins and direct people (D91); reads never run
 * on Haiku — for the files Claude reads and the chat it answers; what Claude has cost on the deal against its budget,
 * one sum over its jobs, for everyone, with ✎ Budget for admins (OQ34). Under it, the last read's model and cost.
 */
export default function ModelBar({ dealId, meta, state, model, onModel, disabled = false }) {
  const models = (meta.ai?.models || []).filter((entry) => !entry.admins_only || state.can?.opus);
  const lastRun = lastRunLine(state.recent, meta);
  return (
    <div className="bnf-chatbar">
      <div className="bnf-chatbar-row">
        <label className="bnf-chatbar-pick">
          Claude
          <select
            value={model}
            disabled={disabled}
            onChange={(event) => onModel(event.target.value)}
            title="The model that reads the files you attach and answers in the chat. Opus 5.5 is kept to admins and direct people."
          >
            <option value="">Default ({modelLabel(meta, meta.ai?.default_model)})</option>
            {models.map((entry) => (
              <option key={entry.key} value={entry.key}>
                {entry.label}
              </option>
            ))}
          </select>
        </label>
        <span
          className="bnf-chatbar-spend"
          title="What Claude has cost on this deal, every read and reply included, against the deal's Claude budget."
        >
          {spendLine(state.spend)}
        </span>
        {dealId && state.can?.budget && <BudgetEdit dealId={dealId} spend={state.spend} />}
      </div>
      {lastRun && <div className="bnf-msg-cost bnf-lastrun">{lastRun}</div>}
    </div>
  );
}
