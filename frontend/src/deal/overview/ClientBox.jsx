import { Link } from 'react-router';
import { useSetClientStatus } from '../../api/deals';
import { errorText } from '../../lib/errors';

/**
 * The client box (M21, M23 as changed by OQ2; CL4, CL26; old `ClientHeader.jsx`'s `bnf-ov-clientbox`): a New or
 * Existing client is on the client book, and its "<client> ↗" opens the client page (slice 67; M21 Keep, CL26);
 * a prospect is "Not on the client book yet", with Convert to client in the old "Link to client"'s place. Convert goes
 * through the status door (POST clients/{id}/status/, rule 6); the server says when it is refused (a lost deal) and
 * the button shows that sentence. Earlier deals and reminder badges wait with renewals (M22).
 */
export default function ClientBox({ deal, client }) {
  const setStatus = useSetClientStatus(deal);
  const convert = client.convert;

  if (client.on_book) {
    return (
      <div className="bnf-ov-clientbox">
        <Link className="bnf-ov-clientlink" to={`/clients/${client.id}/overview`}>
          {client.name} ↗
        </Link>
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
