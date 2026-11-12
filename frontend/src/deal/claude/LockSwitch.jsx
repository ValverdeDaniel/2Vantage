import { useDealAiSettings } from '../../api/chats';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';

/*
 * The plan table locked from Claude (plan.md §8.17; D104, F113; the old ClaudeLockSwitch): one switch, shown in the
 * drawer's lock row (a pill, with who locked it and a note) and, `compact`, on the Advisor's board toolbar ("Claude
 * can edit" / "Locked from Claude", one of the toolbar's buttons). Locked, Claude still reads and answers, and every
 * change it proposes — a read's or a chat's — waits for review, even for a direct person. Anyone on the deal locks or
 * unlocks it.
 */
function lockTitle(lock) {
  if (lock) {
    return `Locked${lock.by?.name ? ` by ${lock.by.name}` : ''}: Claude can read this table, but every change it suggests waits for your review. Click to let Claude change the table again.`;
  }
  return 'Claude can change this table. Click to lock it: Claude can still read the table, but its changes wait for your review.';
}

export default function LockSwitch({ dealId, lock, compact = false }) {
  const toast = useToast();
  const settings = useDealAiSettings(dealId);
  const on = Boolean(lock);

  async function toggle() {
    try {
      await settings.mutateAsync({ locked: !on });
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  const label = on
    ? compact ? 'Locked from Claude' : "🔒 Claude can't change this table"
    : compact ? 'Claude can edit' : '🔓 Claude can change this table'; // prettier-ignore
  const button = (
    <button
      type="button"
      className={`bnf-claude-lock ${compact ? 'btn btn-secondary btn-sm' : 'pill'}${on ? ' on' : ''}`}
      aria-pressed={on}
      disabled={settings.isPending}
      title={lockTitle(lock)}
      onClick={toggle}
    >
      {compact && <span aria-hidden="true">{on ? '🔒' : '🔓'}</span>}
      <span>{label}</span>
      {on && !compact && lock.by?.name && <span className="bnf-claude-lock-by">· {lock.by.name}</span>}
    </button>
  );
  if (compact) return button;
  return (
    <div className="bnf-wwc-lock-row">
      {button}
      {on && <span className="bnf-wwc-lock-note">Claude reads and answers; its changes wait for your review.</span>}
    </div>
  );
}
