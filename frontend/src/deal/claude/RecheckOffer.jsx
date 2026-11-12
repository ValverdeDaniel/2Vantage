import useRecheck from "./useRecheck";
import { claudeDoor } from "./door";

/*
 * "✦ Re-check N flags ▸" on the Claude strip (plan.md §8.17; E80, D34; slice 22; the old CaseWorkspace's strip line):
 * past the server's `suggest` open warnings on the deal, a second read of just the flagged values often settles them.
 * It starts ✦ Ask Claude to re-check over every flag on the deal; its card waits in the drawer for a person to apply.
 * The ✕ hides it for the visit.
 */
const KEY = "recheck-offer";

export default function RecheckOffer({ dealId, flags, dismissed }) {
  const recheck = useRecheck(dealId);
  if (
    !recheck ||
    !flags?.suggest ||
    flags.open <= flags.suggest ||
    dismissed.includes(KEY)
  )
    return null;
  return (
    <div
      className="bnf-claude-strip bnf-claude-strip-news"
      data-claude-strip="recheck"
    >
      <span className="bnf-claude-strip-text">
        ✦ {flags.open} AI values to review — a second read of just the flagged
        values often settles them.
      </span>
      <button
        type="button"
        className="btn btn-secondary btn-sm bnf-review-btn-claude"
        disabled={recheck.busy}
        onClick={() => recheck.run({})}
      >
        ✦ Re-check {flags.open} flags ▸
      </button>
      <button
        type="button"
        className="bnf-claude-strip-x"
        aria-label="Dismiss"
        onClick={() => claudeDoor.dismiss(KEY)}
      >
        ✕
      </button>
    </div>
  );
}
