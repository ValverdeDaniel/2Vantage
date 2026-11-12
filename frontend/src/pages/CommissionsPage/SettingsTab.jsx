import { useState } from 'react';
import { useCommissionSettings, useSaveSettings } from '../../api/commission';
import { useMeta } from '../../api/meta';
import CompInput from '../../deal/shared/CompInput';
import { errorText } from '../../lib/errors';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import { useToast } from '../../ui/useToast';

/*
 * Settings (H100; 891f1b3 `commissions/SettingsTab.jsx`, its words and classes): the firm's producer share for year
 * one and for renewals (the house keeps the rest), and the agency's default rate (H8), all on one screen. A sparse
 * PATCH; saving anything confirms the placeholders. The external-referrer default, the agreement visibility and the
 * gap grace are not built (dead fields, comp agreements and the ledger; H.6, OQ6).
 */
export default function SettingsTab() {
  const toast = useToast();
  const meta = useMeta().data;
  const settings = useCommissionSettings();
  const save = useSaveSettings();
  const [draft, setDraft] = useState({});
  const [errors, setErrors] = useState({});

  if (settings.isPending || !meta) return <Loading label="Loading..." />;
  if (settings.isError) return <InlineError title="Settings" error={settings.error} onRetry={() => settings.refetch()} />;

  const stored = settings.data;
  const value = (key) => (key in draft ? draft[key] : stored[key]);
  const dirty = Object.keys(draft).length > 0;

  function submit() {
    setErrors({});
    save.mutate(dirty ? draft : { confirm: true }, {
      onSuccess: () => setDraft({}),
      onError: (error) => {
        const body = error?.response?.data;
        if (body && typeof body === 'object') setErrors(body);
        toast.error(errorText(error));
      },
    });
  }

  const pctRow = (label, key, hint) => (
    <div>
      <div className="bnf-com-row">
        <div className="bnf-com-row-label">{label}</div>
        <span className="bnf-com-inline-edit">
          <input value={value(key) ?? ''} aria-label={label} onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} />
          <span className="bb-drop-meta">
            % producer{key in draft ? '' : ` · ${stored[key.replace('_pct', '_house_pct')]}% house`}
          </span>
        </span>
      </div>
      {hint && <div className="bb-drop-meta" style={{ marginTop: -4, marginBottom: 6 }}>{hint}</div>}
      {errors[key] && <div className="bnf-com-row-err" style={{ paddingLeft: 0 }}>{errors[key]}</div>}
    </div>
  );

  return (
    <div className="bnf-com-settings">
      {stored.confirmed ? (
        <div className="bnf-com-confirmed">Defaults confirmed{stored.confirmed_by ? ` by ${stored.confirmed_by}` : ''}.</div>
      ) : (
        <div className="bnf-com-placeholder">
          These are placeholders from the 8/18 call (&quot;$1,000 → 60 % house / 40 % producer; year one higher, renewals
          lower&quot;). Confirm them with Stephanie — saving here marks them confirmed.
        </div>
      )}

      <div className="bb-panel" data-guide="settings-defaults">
        <div className="bb-panel-title">House / producer split defaults</div>
        <div className="bb-panel-sub">
          Used when a producer has no share of their own (set those on Producers &amp; partners). Split producers divide
          only the producer&apos;s share.
        </div>
        {pctRow('First-year producer share', 'first_year_pct')}
        {pctRow('Renewal producer share', 'renewal_pct', 'Renewals pay the house more — it services the account.')}

        <div className="bnf-com-row">
          <div className="bnf-com-row-label">Agency default rate</div>
          <CompInput small types={meta.commission_types || []} value={value('default_commission')}
            label="Agency default rate" onCommit={(comp) => setDraft({ ...draft, default_commission: comp || '' })} />
          <span className="bb-drop-meta">what every line asks the carriers for until the deal agrees its own</span>
        </div>
        {errors.default_commission && (
          <div className="bnf-com-row-err" style={{ paddingLeft: 0 }}>{errors.default_commission}</div>
        )}

        <div className="bnf-com-actions">
          {dirty && (
            <button type="button" className="btn btn-secondary btn-sm" disabled={save.isPending}
              onClick={() => { setDraft({}); setErrors({}); }}>
              Discard
            </button>
          )}
          <button type="button" className="btn btn-primary btn-sm" onClick={submit} disabled={save.isPending}>
            {save.isPending ? 'Saving…' : dirty ? 'Save' : stored.confirmed ? 'Saved' : 'Confirm these defaults'}
          </button>
        </div>
      </div>
    </div>
  );
}
