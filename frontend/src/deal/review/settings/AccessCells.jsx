import { useState } from 'react';
import { useClientContacts } from '../../../api/review';
import { useGiveAccess } from '../../../api/reviewForm';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import WhoGetsIt from '../newlink/WhoGetsIt';
import PinOnce from '../request/PinOnce';

/*
 * Who gets it, on a link's settings card (plan.md §8.8; L39, L63, L72; old 891f1b3 `LinkSettingsCard.jsx`
 * `CorrectAddress`, `GiveAccess`): a mistyped address, while nobody has opened the link (this link only: the contact
 * keeps their own), and someone else's own link on the same request, asking the same things, its PIN shown once.
 * Both act at once.
 */
export function CorrectAddress({ person, actions }) {
  const [value, setValue] = useState(null);
  if (value === null) {
    return (
      <button type="button" className="rr-linklike" onClick={() => setValue(person.email || '')}
        title="A typing mistake: nobody has opened this link yet, so its address can still change">
        {person.email ? 'Correct the address' : 'Add an address'}
      </button>
    );
  }
  const save = async () => {
    const answer = await actions.setting(person, 'address', { email: value.trim() }, 'Address corrected on this link', false);
    if (answer) setValue(null);
  };
  return (
    <div className="rr-edit-address">
      <input type="email" value={value} aria-label="The right address" onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') save();
          if (event.key === 'Escape') setValue(null);
        }} />
      <button type="button" className="btn btn-sm btn-primary" disabled={actions.busy || !value.trim()} onClick={save}>
        Save
      </button>
      <button type="button" className="btn btn-sm btn-secondary" onClick={() => setValue(null)}>
        Cancel
      </button>
      <div className="rr-edit-note">This link only: the contact on the deal keeps their own address.</div>
    </div>
  );
}

export function GiveAccess({ deal, person, name }) {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState({ contactIds: [], typed: [] });
  const [made, setMade] = useState([]);
  const contacts = useClientContacts(deal.id, deal.client.id);
  const give = useGiveAccess(deal.id);
  const toast = useToast();
  const people = [...state.contactIds.map((id) => ({ contact_id: id })), ...state.typed.map(({ name: who, email }) => ({ name: who, email }))];
  const submit = () =>
    give
      .mutateAsync({ requestId: person.request_id, people })
      .then((answer) => {
        toast.success(`${answer.links.length} new link${answer.links.length === 1 ? '' : 's'} made: copy it from their name on the who bar`);
        setMade(answer.links.filter((link) => link.pin));
        setOpen(false);
        setState({ contactIds: [], typed: [] });
      })
      .catch((error) => toast.error(errorText(error, { fallback: 'Could not make that link.' })));
  if (!open) {
    return (
      <>
        <button type="button" className="rr-linklike rr-edit-give" onClick={() => setOpen(true)} title="They get their own link, asking the same things">
          ＋ Give someone else access
        </button>
        {made.map((link) => (
          <PinOnce key={link.link_id} pin={link.pin} name={link.name} />
        ))}
      </>
    );
  }
  return (
    <div className="rr-edit-give-box">
      <div className="rr-edit-note">
        They get their own link, asking the same things. {person.name ? `If ${name} should no longer have this one, turn it off above:` : 'If this one should stop opening, turn it off above:'} a
        link already sent can’t be taken back any other way.
      </div>
      <WhoGetsIt contacts={contacts.data?.contacts || []} state={state} onChange={(part) => setState((now) => ({ ...now, ...part }))}
        disabled={give.isPending} dealId={deal.id} clientId={deal.client.id} />
      <div className="rr-person-actions">
        <button type="button" className="btn btn-sm btn-violet" disabled={give.isPending || !people.length} onClick={submit}
          title="Make their link: nothing goes out until you copy it to them">
          {give.isPending ? 'Making it…' : 'Give them access'}
        </button>
        <button type="button" className="btn btn-sm btn-secondary" disabled={give.isPending} onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
    </div>
  );
}
