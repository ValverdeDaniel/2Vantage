import { useTray, useTrayAsk } from '../../api/reviewTray';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { askedOn, trayState } from './trayAsk';

/*
 * "＋ Ask" / "✓ In tray" / "Asked Oct 20" for one item outside the Review tab (plan.md §8.8; L54; B12, B27; old 891f1b3
 * IntakeTab `bnf-ask-btn`, `bnf-in-tray`): a click puts the item in the deal's request tray, where it waits with
 * everything else asked until a person sends it, on one link (OQ87: nothing reaches the client before then). One tray
 * read for the whole deal page (`useTray`), so every button agrees. Absent when the deal may no longer ask its client.
 */
export default function AskButton({ dealId, refName, label = '＋ Ask', title, className = 'bnf-ask-btn', inTrayWords = '✓ In tray' }) {
  const tray = useTray(dealId);
  const ask = useTrayAsk(dealId);
  const toast = useToast();
  const found = trayState(tray.data, refName);
  if (!tray.data || found.state === 'closed') return null;
  if (found.state === 'in_tray') {
    return (
      <span className="bnf-in-tray" title="Waiting in the request tray">
        {inTrayWords}
      </span>
    );
  }
  if (found.state === 'asked') {
    return (
      <span className="bnf-in-tray" title="On a link they have: it shows on their form">
        Asked {askedOn(found.at)}
      </span>
    );
  }
  return (
    <button
      type="button"
      className={className}
      disabled={ask.isPending}
      title={title || 'Add it to the request tray: it goes with everything else you ask for, on one link'}
      onClick={(event) => {
        event.stopPropagation();
        ask
          .mutateAsync({ refs: [refName] })
          .then(() => toast.success('Added to the request tray'))
          .catch((error) => toast.error(errorText(error)));
      }}
    >
      {label}
    </button>
  );
}
