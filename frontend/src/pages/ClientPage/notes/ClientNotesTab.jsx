import { useState } from 'react';
import { Link } from 'react-router';
import { useClientWrites } from '../../../api/clientPage';
import { NotesCard } from '../../../deal/overview';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';

// The brief's textarea, kept as typed until it is saved on blur (the old tab's `bnf-cw-brief`).
function StandingBrief({ client, writes }) {
  const [brief, setBrief] = useState(null); // null: showing the saved brief
  const toast = useToast();
  const shown = brief ?? client.notes ?? '';
  const save = () => {
    const text = (brief ?? '').trim();
    if (brief === null || text === (client.notes || '').trim()) {
      setBrief(null);
      return;
    }
    writes.update.mutate(
      { notes: text },
      {
        onSuccess: () => {
          setBrief(null);
          toast.success('Standing brief saved');
        },
        onError: (error) => toast.error(errorText(error, { fallback: 'Could not save the brief.' })),
      },
    );
  };
  return (
    <div className="bb-panel">
      <div className="bb-panel-title">Standing brief</div>
      <div className="bb-panel-sub">
        What someone new to this account should know — decision makers, sensitivities, how they like to be worked.
        Internal.
      </div>
      <textarea
        className="bnf-ov-note-input bnf-cw-brief"
        rows={4}
        aria-label="Standing brief"
        placeholder="e.g. Owner decides, HR executes. Hates surprises at renewal — walk them through the numbers 60 days out…"
        value={shown}
        disabled={writes.update.isPending}
        onChange={(event) => setBrief(event.target.value)}
        onBlur={save}
      />
      <div className="bb-drop-meta">Saves when you click away.</div>
    </div>
  );
}

/**
 * The client's Notes tab (plan.md §8.5; CL23; old ClientNotesTab.jsx at 891f1b3): the standing brief on the client
 * (`Client.notes`, saved on blur through deals' PATCH) and the running notepad of the deal the page works in — the
 * deal's own notes card, with its kinds, pins, edits and Undo. Earlier deals' notes wait with renewals (M78).
 */
export default function ClientNotesTab({ client, overview }) {
  const dealId = overview.deal_id;
  const writes = useClientWrites(client.id, dealId);
  const year = overview.history.find((row) => row.deal_id === dealId)?.year;
  return (
    <div className="bb-tab-page">
      <div className="bnf-ov-titlerow">
        <div>
          <div className="bb-tab-title">Notes</div>
          <div className="bb-subtitle">The standing brief on the relationship, then the running notepad of its deal.</div>
        </div>
      </div>
      <StandingBrief client={client} writes={writes} />
      {dealId ? (
        <div className="bnf-cw-notes">
          <NotesCard
            dealId={dealId}
            title={`Notepad · ${year || 'current'} deal`}
            sub={
              <>
                Notes live on the deal they were written on — this is the{' '}
                {overview.current ? 'deal in flight' : 'latest deal'} (<Link to={`/deals/${dealId}/overview`}>open ↗</Link>
                ).
              </>
            }
          />
        </div>
      ) : (
        <div className="bb-panel empty-state">
          The notepad lives on deals — this client has none yet, so there is nothing to note against.
        </div>
      )}
    </div>
  );
}
