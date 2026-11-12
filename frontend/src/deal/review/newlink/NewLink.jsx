import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { planRequest, reviewKey, useClientContacts, useCreateRequest } from '../../../api/review';
import { errorText } from '../../../lib/errors';
import { useDebouncedValue } from '../../../lib/useDebouncedValue';
import { monthDay } from '../reviewModel';
import { asksOf, bodyOf, createWords, dayIn, floorKey, hasAsk, initialState, whoCount } from './newLinkModel';
import WhatToAsk from './WhatToAsk';
import WhoCanOpen from './WhoCanOpen';
import WhoGetsIt from './WhoGetsIt';

const FILLED = 'What we have shows, for them to check or change.';
const BLANK = 'Only what they answer shows, never what else we hold.';

/*
 * New link settings (L40, L55–L57, L61, L64, L66; old 891f1b3 `LinkSettingsCard.jsx` `NewLinkSettings`), the minimal
 * builder: who gets it, what to ask, who can open it, what they see, when it expires and a note. Nothing is saved
 * until Create link; the server's dry run (after 350 ms) says the lowest level what is picked allows. `onCreated`
 * receives the server's answer (each link and any PIN, this once).
 */
export default function NewLink({ deal, meta, onCreated, onCancel }) {
  const [state, setState] = useState(initialState);
  const contacts = useClientContacts(deal.id, deal.client.id);
  const create = useCreateRequest(deal.id);
  const asked = useDebouncedValue(floorKey(state), 350);
  const floor = useQuery({
    queryKey: reviewKey(deal.id, 'floor', asked),
    queryFn: () => planRequest(deal.id, { asks: JSON.parse(asked), people: [] }),
    enabled: asked !== '{}',
    staleTime: Infinity,
  });
  const change = (part) => setState((now) => ({ ...now, ...part }));
  const ready = hasAsk(state) && asked === floorKey(state);
  const latest = dayIn(meta?.ceiling_days ?? 30);
  const waitingOn = !hasAsk(state) ? 'Pick something to ask for.' : '';

  function submit() {
    create.mutate(bodyOf(state), {
      onSuccess: (answer) => {
        setState(initialState());
        onCreated(answer);
      },
    });
  }

  return (
    <div className="rr-newlink" role="group" aria-label="New link settings">
      <div className="rr-newlink-head">
        <b>New link settings</b>
        <span className="rr-edit-note">Nothing is saved until Create link.</span>
        <span className="rr-settings-actions">
          <button type="button" className="btn btn-sm btn-violet" disabled={create.isPending || Boolean(waitingOn)}
            title={waitingOn || 'Make a personal link for each person picked: nothing is emailed, you copy and share it next'}
            onClick={submit}>
            {createWords(state, create.isPending)}
          </button>
          <button type="button" className="rr-linklike" title="Leave without making a link: what you picked here goes"
            onClick={() => {
              setState(initialState());
              onCancel();
            }}>
            Cancel
          </button>
        </span>
      </div>
      {(create.isError || waitingOn) && (
        <div className="rr-edit-note" role="status">
          {create.isError ? errorText(create.error, { fallback: 'Could not create the link.' }) : waitingOn}
        </div>
      )}
      <div className="rr-newlink-grid">
        <div className="rr-newlink-h">Who gets it</div>
        <div>
          <WhoGetsIt contacts={contacts.data?.contacts || []} state={state} onChange={change} disabled={create.isPending} />
          {whoCount(state) > 1 && (
            <div className="rr-edit-note">
              Everyone gets the same questions and their own link, and what one of them enters saves to the same place.
            </div>
          )}
          {whoCount(state) === 0 && (
            <div className="rr-edit-note">No one named: a private link you can paste anywhere. Pick a person to make it theirs.</div>
          )}
        </div>
        <div className="rr-newlink-h">What to ask</div>
        <WhatToAsk meta={meta} state={state} onChange={change} disabled={create.isPending} />
        <div className="rr-newlink-h">Who can open it</div>
        <WhoCanOpen meta={meta} security={state.security} floor={ready ? floor.data?.floor : null} onChange={change}
          disabled={create.isPending} />
        <div className="rr-newlink-h">What they see</div>
        <div className="rr-newlink-levels" role="radiogroup" aria-label="What they see">
          <label className="rr-edit-level">
            <input type="radio" name="newlink-view" checked={!state.blank} onChange={() => change({ blank: false })} />
            <span><b>Filled in</b> {FILLED}</span>
          </label>
          <label className="rr-edit-level">
            <input type="radio" name="newlink-view" checked={state.blank} onChange={() => change({ blank: true })} />
            <span><b>Blank</b> {BLANK}</span>
          </label>
        </div>
        <div className="rr-newlink-h">Expires</div>
        <div className="rr-edit-row">
          <input type="date" aria-label="When this link runs out" min={dayIn(0)} max={latest}
            value={state.expiresOn || dayIn(meta?.life_days ?? 7)} onChange={(e) => change({ expiresOn: e.target.value })} />
          <span className="rr-edit-note">
            latest {monthDay(`${latest}T12:00:00`)}.{' '}
            {state.expiresOn ? 'A date you pick holds: their saves no longer push it out.' : 'Their saves push it out until then.'}
          </span>
        </div>
        <div className="rr-newlink-h">A note for them</div>
        <textarea rows={2} maxLength={meta?.message_limit ?? 1000} value={state.message} aria-label="A note for them"
          placeholder="Shown at the top of their page." onChange={(e) => change({ message: e.target.value })} />
      </div>
      {Object.keys(asksOf(state)).length > 0 && floor.isError && (
        <div className="rr-edit-note">{errorText(floor.error, { fallback: 'Could not check what this asks.' })}</div>
      )}
    </div>
  );
}
