import { useState } from 'react';
import { useParties, useSaveParty } from '../../api/commission';
import { useMeta } from '../../api/meta';
import { errorText } from '../../lib/errors';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import { useToast } from '../../ui/useToast';
import AddPartyForm from './AddPartyForm';
import { PartnersTable, ProducersTable } from './PartyTables';

/*
 * Producers & partners (H95–H98, H101; 891f1b3 `commissions/PartiesTab.jsx`, its words and classes): "show inactive",
 * the all tier's "＋ Add external broker / partner" form, the producers (logins without a Party listed too; they get
 * one on their first edit or split save, H95) and the partners. The all tier edits inline; the own tier sees the
 * roster only. The profile drawer and "book ↗" wait (H99; the Book is slice 49).
 */
export default function PartiesTab({ isAll }) {
  const toast = useToast();
  const meta = useMeta().data;
  const [inactive, setInactive] = useState(false);
  const [adding, setAdding] = useState(false);
  const roster = useParties(inactive);
  const save = useSaveParty();

  if (roster.isPending || !meta) return <Loading label="Loading..." />;
  if (roster.isError) return <InlineError title="Producers & partners" error={roster.error} onRetry={() => roster.refetch()} />;

  /** An inline edit: PATCH a Party, or POST a login's first Party (`user`) for a computed row. */
  function edit(entry, changes, done) {
    const body = entry.id ? { id: entry.id, changes } : { changes: { user: entry.user, ...changes } };
    save.mutate(body, {
      onSuccess: () => done && toast.success(done),
      onError: (error) => toast.error(errorText(error)),
    });
  }

  return (
    <div>
      <div className="bnf-com-filters">
        <label className="bnf-com-active">
          <input type="checkbox" checked={inactive} onChange={(event) => setInactive(event.target.checked)} /> show
          inactive
        </label>
        {isAll && (
          <button type="button" className="btn btn-primary btn-sm" style={{ marginLeft: 'auto' }}
            onClick={() => setAdding((open) => !open)}>
            {adding ? 'Cancel' : '＋ Add external broker / partner'}
          </button>
        )}
      </div>

      {adding && isAll && <AddPartyForm meta={meta} onAdded={() => setAdding(false)} />}

      <div className="bnf-com-section-title">Producers</div>
      <ProducersTable rows={roster.data.producers} isAll={isAll} busy={save.isPending} meta={meta} onEdit={edit} />

      <div className="bnf-com-section-title">External brokers &amp; COI partners</div>
      <PartnersTable rows={roster.data.partners} isAll={isAll} busy={save.isPending} meta={meta} onEdit={edit} />

      <div className="bb-drop-meta" style={{ marginTop: 10 }}>
        The house is fixed — its share comes from each producer’s own year-1 / renewal share, or the firm defaults.
      </div>
    </div>
  );
}
