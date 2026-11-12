import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import api from '../../api/client';
import { useCreateClient } from '../../api/deals';
import { PROSPECT, useMeta } from '../../api/meta';
import { QuoteDrop } from '../../deal/claude';
import { formErrorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import ExistingClients from '../HomePage/ExistingClients';

/*
 * The New deal page (`/deals/new`; plan.md §8.3; A14, D43; the old shared/NewCase.jsx): the two old mode cards, then
 * Group name *, Renewal date and Notes (the deal's first note). Both make a Prospect and its deal.
 * - "1 · Get to Market — New client, start the intake": Create deal & open intake ▸.
 * - "2 · Quote to Close — I already have carrier quotes" (only with Claude set up, D26): Work with Claude opens on
 *   the page; the first files dropped or attached make the deal, are filed as carrier quotes and read at once, and the
 *   deal opens on its Advisor with the drawer open on the read (D43: 2V reviews plans there; an admin's or a direct
 *   person's read lands with Undo, anyone else's waits there for review). The mode is in the URL (`?mode=quotes`).
 * Once the deal is made the fields lock, so what made it cannot drift.
 */
const NOTE_SAID = 'Saved as the deal’s first note. Once the deal is made, tell Claude what the client wants there.';

export default function NewDealPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { data: meta } = useMeta();
  const create = useCreateClient();
  const [params, setParams] = useSearchParams();
  const quotesOn = Boolean(meta?.ai);
  const mode = params.get('mode') === 'quotes' && quotesOn ? 'quotes' : 'intake';
  const [name, setName] = useState('');
  const [date, setDate] = useState('');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');
  const [showScan, setShowScan] = useState(true);
  const [madeId, setMadeId] = useState(null); // the deal, once made: the fields lock
  const made = useRef(null); // and a second drop never makes another

  useEffect(() => {
    document.title = 'New deal — 2Vantage';
  }, []);

  const setMode = (next) => {
    if (madeId) return;
    const changed = new URLSearchParams(params);
    if (next === 'quotes') changed.set('mode', 'quotes');
    else changed.delete('mode');
    setParams(changed, { replace: true });
  };

  async function ensureDeal() {
    if (made.current) return made.current;
    if (!name.trim()) {
      setError('Enter the group name first.');
      return null;
    }
    setError('');
    try {
      const { client, deal } = await create.mutateAsync({
        name: name.trim(),
        relationship: PROSPECT,
        effective_date: date || null,
      });
      made.current = deal.id;
      setMadeId(deal.id);
      if (notes.trim()) {
        // the deal's first note (A14), through the deal's notes (slice 38); the deal stands even if it fails
        await api.post(`deals/${deal.id}/notes/`, { body: notes.trim() }).catch(() => {
          toast.error('The deal was made, but its note could not be saved. Add it on the deal.');
        });
      }
      toast.success(`Created ${client.name}.`);
      return deal.id;
    } catch (failure) {
      setError(formErrorText(failure, []) || 'Could not create the deal.');
      return null;
    }
  }

  async function openIntake() {
    const id = await ensureDeal();
    if (id) navigate(`/deals/${id}/intake`);
  }

  const card = (key, eyebrow, title, sub) => (
    <div
      className={`bnf-mode-card ${mode === key ? 'active' : ''}`}
      role="button"
      tabIndex={0}
      aria-pressed={mode === key}
      onClick={() => setMode(key)}
      onKeyDown={(event) => (event.key === 'Enter' || event.key === ' ') && setMode(key)}
    >
      <div className="bnf-mode-card-eyebrow">{eyebrow}</div>
      <div className="bnf-mode-card-title">{title}</div>
      <div className="bnf-mode-card-sub">{sub}</div>
    </div>
  );

  const locked = Boolean(madeId) || create.isPending;
  return (
    <div className="bb-upload-page">
      <Link to="/" className="bb-back-link">
        ← Benefits
      </Link>
      <div className="bb-title bb-title-sm" role="heading" aria-level={1}>
        New benefits deal
      </div>
      <div className="bb-subtitle bb-mb-lg">
        {mode === 'intake'
          ? 'Start with the client — collect their information, census, and authorizations, then send the group to market.'
          : 'Drop the carrier quotes into Claude and it reads them into a side-by-side comparison.'}
      </div>
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
      <div className="bnf-mode-row">
        {card('intake', '1 · Get to Market', 'New client — start the intake', 'Collect the group’s information before going to market.')}
        {quotesOn &&
          card('quotes', '2 · Quote to Close', 'I already have carrier quotes', 'Scan the quotes and build the side-by-side comparison now.')}
      </div>
      <div className="bb-upload-fields">
        <div className="form-group">
          <label htmlFor="new-deal-name">Group name *</label>
          <input
            id="new-deal-name"
            type="text"
            value={name}
            maxLength={200}
            disabled={locked}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. Harbor Point Manufacturing"
          />
        </div>
        <div className="form-group">
          <label htmlFor="new-deal-date">Renewal date</label>
          <input
            id="new-deal-date"
            type="date"
            value={date}
            disabled={locked}
            onChange={(event) => setDate(event.target.value)}
          />
        </div>
      </div>
      <ExistingClients name={name} />
      <div className="form-group bnf-newcase-notes">
        <label htmlFor="new-deal-notes">Notes</label>
        <textarea
          id="new-deal-notes"
          rows={3}
          value={notes}
          disabled={locked}
          onChange={(event) => setNotes(event.target.value)}
          placeholder="What you know so far — e.g. Medical renewal · 12 EEs · they want to keep the PPO network"
        />
        <div className="bb-drop-meta">{NOTE_SAID}</div>
      </div>
      {mode === 'quotes' ? (
        <>
          {!showScan && (
            <button type="button" className="btn btn-primary bb-run-btn" onClick={() => setShowScan(true)}>
              Scan the quotes with Claude ▸
            </button>
          )}
          {showScan && (
            <QuoteDrop
              ensureDeal={ensureDeal}
              onSent={(dealId) => navigate(`/deals/${dealId}/advisor?claude=1`)}
              onClose={() => setShowScan(false)}
            />
          )}
        </>
      ) : (
        <button type="button" className="btn btn-primary bb-run-btn" disabled={locked} onClick={openIntake}>
          Create deal &amp; open intake ▸
        </button>
      )}
    </div>
  );
}
