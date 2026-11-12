import { useState } from 'react';
import { useSaveParty } from '../../api/commission';
import CompInput from '../../deal/shared/CompInput';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';

/*
 * "New partner" (H96; the old PartiesTab form, its words and classes): a referring agent, or a producer without a
 * login yet. The kinds come from /api/meta/ `commission.kinds`.
 */
const EMPTY = { kind: 'partner', name: '', email: '', npn: '', appointed: false, default_split: null };

export default function AddPartyForm({ meta, onAdded }) {
  const toast = useToast();
  const save = useSaveParty();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const set = (patch) => setForm((current) => ({ ...current, ...patch }));

  function submit(event) {
    event.preventDefault();
    setErrors({});
    save.mutate(
      { changes: { ...form, default_split: form.default_split || '' } },
      {
        onSuccess: () => {
          toast.success('Added');
          setForm(EMPTY);
          onAdded();
        },
        onError: (error) => {
          const body = error?.response?.data;
          if (body && typeof body === 'object') setErrors(body);
          toast.error(errorText(error));
        },
      },
    );
  }

  const messages = Object.values(errors).flat().filter((value) => typeof value === 'string');
  return (
    <form className="bb-panel" onSubmit={submit} style={{ marginBottom: 16 }}>
      <div className="bb-panel-title">New partner</div>
      <div className="bb-panel-sub">A referring life-insurance agent, or a producer without a login yet.</div>
      <div className="bnf-com-party-form">
        <label>
          Kind
          <select value={form.kind} onChange={(event) => set({ kind: event.target.value })}>
            {meta.commission.kinds.map((entry) => (
              <option key={entry.key} value={entry.key}>
                {entry.key === 'producer' ? 'Producer (no login)' : 'External broker (referrer)'}
              </option>
            ))}
          </select>
        </label>
        <label>
          Name
          <input value={form.name} required onChange={(event) => set({ name: event.target.value })}
            placeholder="Riverside Life Partners" />
        </label>
        <label>
          Email
          <input value={form.email} onChange={(event) => set({ email: event.target.value })} placeholder="optional" />
        </label>
        <label>
          NPN
          <input value={form.npn} onChange={(event) => set({ npn: event.target.value })} placeholder="optional" />
        </label>
        <label>
          Default split
          <CompInput small types={meta.commission_types || []} value={form.default_split} label="Default split"
            onCommit={(comp) => set({ default_split: comp })} />
        </label>
        <label className="bnf-com-active" style={{ alignSelf: 'center' }}>
          <input type="checkbox" checked={form.appointed} onChange={(event) => set({ appointed: event.target.checked })} />{' '}
          appointed &amp; licensed
        </label>
        <button className="btn btn-primary btn-sm" type="submit" disabled={save.isPending}>
          Add
        </button>
      </div>
      {messages.length > 0 && (
        <div className="bnf-com-row-err" style={{ paddingLeft: 0 }}>
          {messages.join(' · ')}
        </div>
      )}
    </form>
  );
}
