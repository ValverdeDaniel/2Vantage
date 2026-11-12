import { useRef, useState } from 'react';
import { useClearBor, useSignBor } from '../../api/intake';
import { errorText } from '../../lib/errors';
import { formatDate } from '../../lib/format';
import { useToast } from '../../ui/useToast';
import useChecklistWrites from './useChecklistWrites';

/*
 * Compliance & authorizations (plan.md §8.9; B29, B31), the old Intake card (891f1b3 `IntakeTab.jsx`, same classes):
 * the BOR e-signature — a typed name stamps who and when ("Signed by …", "<date> · e-sign record"), and (B29's fix)
 * it can be cleared — then one row per compliance upload (BOR letter, carrier authorization, claims experience,
 * the 5500, plan documents; the list and its words are the server's) with the files on the deal and Attach. A BOR
 * letter on file puts the BOR on file too (§5.2). An earlier year's BOR (B30) waits with renewals.
 */
function ComplianceRow({ row, accept, busy, onAttach }) {
  const fileRef = useRef(null);
  return (
    <div className="bnf-doc-row bnf-compliance-row">
      <span className="bnf-doc-icon">📄</span>
      <span className="bnf-doc-name">{row.label}</span>
      {row.documents.map((doc) => (
        <span key={doc.id} className="bb-badge bb-badge-green" title={doc.name}>
          {doc.name}
        </span>
      ))}
      <input
        ref={fileRef}
        type="file"
        accept={accept}
        style={{ display: 'none' }}
        aria-label={`Attach ${row.label}`}
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = '';
          if (file) onAttach(row.kind, row.label, file);
        }}
      />
      <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => fileRef.current?.click()}>
        Attach
      </button>
    </div>
  );
}

export default function AuthorizationsCard({ deal, meta, bor, compliance }) {
  const toast = useToast();
  const sign = useSignBor(deal.id);
  const clear = useClearBor(deal.id);
  const uploads = useChecklistWrites(deal.id);
  const [name, setName] = useState('');
  const busy = sign.isPending || clear.isPending || uploads.busy;
  const acceptOf = (kind) => (meta?.document_kinds || []).find((entry) => entry.key === kind)?.accept?.join(',') || '';

  const signNow = () => {
    if (!name.trim()) return;
    sign.mutate(name.trim(), {
      onSuccess: () => {
        setName('');
        toast.success('BOR signed');
      },
      onError: (error) => toast.error(errorText(error, { fallback: 'Could not record the signature.' })),
    });
  };

  return (
    <div className="bb-panel bnf-intake-section">
      <div className="bb-panel-title">Compliance &amp; authorizations</div>
      <div className="bb-panel-sub">BOR must be signed before carrier submission</div>
      <div className="bnf-subcard bnf-esign-card">
        {bor?.signed_at ? (
          <div className="bnf-esign-done">
            <span className="bb-check">✓</span>
            <div>
              <div className="bnf-esign-name">Signed by {bor.name}</div>
              <div className="bb-drop-meta" title={bor.by_name ? `Recorded by ${bor.by_name}` : undefined}>
                {formatDate(bor.signed_at)} · e-sign record ·{' '}
                <button
                  type="button"
                  className="bnf-linklike"
                  disabled={busy}
                  title="Clear the signature; it can be signed again"
                  onClick={() => clear.mutate(undefined, { onError: (error) => toast.error(errorText(error)) })}
                >
                  Clear
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="bnf-subcard-row">
            <input
              className="bnf-intake-input"
              value={name}
              placeholder="Signer full name (BOR)"
              aria-label="Signer full name (BOR)"
              maxLength={200}
              onChange={(event) => setName(event.target.value)}
              onKeyDown={(event) => event.key === 'Enter' && signNow()}
            />
            <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={signNow}>
              Sign BOR
            </button>
          </div>
        )}
      </div>
      {(compliance || []).map((row) => (
        <ComplianceRow key={row.kind} row={row} accept={acceptOf(row.kind)} busy={busy} onAttach={uploads.attach} />
      ))}
    </div>
  );
}
