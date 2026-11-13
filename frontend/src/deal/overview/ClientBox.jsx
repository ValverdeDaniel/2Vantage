import { useState } from 'react';
import { useSetClientStatus } from '../../api/deals';
import { errorText } from '../../lib/errors';
import ClientDialog from '../../pages/DealPage/ClientDialog';

// A link-styled button: the box's link opens the client dialog until slice 67 brings the client page.
const LINK_BUTTON = { background: 'none', border: 0, padding: 0, cursor: 'pointer', fontFamily: 'inherit' };

/**
 * The client box (M21, M23 as changed by OQ2; CL4, CL26; old `ClientHeader.jsx`'s `bnf-ov-clientbox`): a New or
 * Existing client is on the client book, and its "<client> ↗" opens the client (the client dialog until slice 67);
 * a prospect is "Not on the client book yet", with Convert to client in the old "Link to client"'s place. Convert goes
 * through the status door (POST clients/{id}/status/, rule 6); the server says when it is refused (a lost deal) and
 * the button shows that sentence. Earlier deals and reminder badges wait with renewals (M22).
 */
export default function ClientBox({ deal, client, meta }) {
  const [open, setOpen] = useState(false);
  const setStatus = useSetClientStatus(deal);
  const convert = client.convert;

  if (client.on_book) {
    return (
      <div className="bnf-ov-clientbox">
        <button type="button" className="bnf-ov-clientlink" style={LINK_BUTTON} onClick={() => setOpen(true)}>
          {client.name} ↗
        </button>
        {open && <ClientDialog deal={deal} meta={meta} onClose={() => setOpen(false)} />}
      </div>
    );
  }
  return (
    <div className="bnf-ov-clientbox">
      <div className="bb-drop-meta bnf-ov-nolink">Not on the client book yet</div>
      {convert && (
        // A disabled button takes no pointer events, so the refusal's tooltip comes from the span around it.
        <span title={convert.allowed ? undefined : convert.sentence}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={!convert.allowed || setStatus.isPending}
            aria-label={convert.allowed ? undefined : `Convert to client — ${convert.sentence}`}
            onClick={() => setStatus.mutate('new_client')}
          >
            Convert to client
          </button>
        </span>
      )}
      {convert && !convert.allowed && <div className="bnf-ov-clientnext">{convert.sentence}</div>}
      {setStatus.isError && (
        <div role="alert" className="bb-rose bnf-ov-clientnext">
          {errorText(setStatus.error)}
        </div>
      )}
    </div>
  );
}
