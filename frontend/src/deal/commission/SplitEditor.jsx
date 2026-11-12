import { useMemo } from 'react';
import { formatMoney } from '../../lib/format';
import Button from '../../ui/Button';
import PartySelect from '../../ui/PartySelect';
import SplitPreview from './SplitPreview';
import SplitRow from './SplitRow';
import * as model from './splitModel';
import useSplitDraft from './useSplitDraft';

/*
 * Producers & splits (H10–H22, H106; 891f1b3 `overview/SplitsPanel.jsx`, its words and classes): the split that
 * applies with its source badge, the primary (producers only; "(not appointed)" greyed), the secondary, split and
 * referral rows with their terms, the live preview, "Applies to" this client or this deal only, Discard and Save.
 * Every producer sees every row (D-066); only the all tier and the owner may save (OQ70), so for anyone else the
 * editor reads only. Mounted on the deal's Commission tab (`dealId`) and, in client scope, on the client page
 * (`clientId`; slice 68). The booked view (H23) joins with booking in slice 49; carry-forward and comp agreements wait.
 */
export default function SplitEditor(props) {
  const { split } = props;
  // A save or a refetch that changes the stored split starts a fresh draft.
  const stamp = `${split.source}:${JSON.stringify(split.rows)}`;
  return <Editor key={stamp} {...props} />;
}

function Editor({ dealId, clientId, split, basis, preview, meta, title = 'Producers & splits' }) {
  const target = useMemo(() => (dealId ? { dealId } : { clientId }), [dealId, clientId]);
  const editor = useSplitDraft({ target, split, basis, preview });
  const { draft, errors } = editor;
  const vocab = meta.commission;
  const people = split.parties || [];
  const locked = !split.can_save;
  const shown = editor.preview;

  const shareOf = (key, role) => {
    const found = key && model.shareFor(shown, key, role);
    return found ? { pct_label: found.pct_label, amount_label: found.amount != null ? formatMoney(found.amount) : '' } : null;
  };
  const primaryShare = shareOf(draft.primary, 'primary');
  const primaryError = model.topError(errors, draft, 'primary');
  const totalError = model.topError(errors, draft, 'split_total');

  return (
    <div className="bb-panel bnf-com-splits" data-guide="overview-splits">
      <div className="bb-panel-title">{title}</div>
      <div className="bb-panel-sub">Who is on the AOR letter, and who gets a piece of the commission.</div>
      <div className="bnf-com-source">
        <span className="bb-badge bb-badge-gray">{split.source_label}</span>
        {split.source === 'client' && dealId && !editor.dirty && (
          <span className="bb-drop-meta"> · change here to override for this deal, or edit on the client</span>
        )}
      </div>

      <div className="bnf-com-row">
        <div className="bnf-com-row-label">
          <span className="bnf-com-kind bnf-com-role-primary">Primary</span>
        </div>
        <PartySelect
          people={people}
          kinds={vocab.role_kinds.primary}
          groups={vocab.kind_groups}
          requireAppointed
          value={draft.primary}
          excludeKeys={draft.rows.map((row) => row.key).filter(Boolean)}
          emptyLabel="Pick the AOR producer…"
          label="Primary producer"
          disabled={locked}
          onChange={(key) => editor.change({ ...draft, primary: key })}
        />
        {primaryShare && (
          <span className="bnf-com-share">
            {primaryShare.pct_label}
            {primaryShare.amount_label ? ` · ${primaryShare.amount_label}` : ''}
          </span>
        )}
      </div>
      {primaryError && <div className="bnf-com-row-err">{primaryError}</div>}

      <div data-guide="splits-rows">
        {vocab.other_roles.map((role) =>
          draft.rows.map((row, index) =>
            row.role === role ? (
              <SplitRow
                key={index}
                row={row}
                people={people}
                meta={meta}
                used={model.usedKeys(draft, index)}
                share={shareOf(row.key, row.role)}
                error={model.rowError(errors, draft, index)}
                disabled={locked}
                onRole={(next) => editor.change(model.changeRole(draft, index, next, people, vocab.role_kinds))}
                onPick={(key) => editor.change(model.pickPerson(draft, index, key, people))}
                onChange={(patch, options) => editor.change(model.setRow(draft, index, patch), options)}
                onRemove={() => editor.change(model.removeRow(draft, index))}
              />
            ) : null,
          ),
        )}
      </div>
      {totalError && <div className="bnf-com-row-err">{totalError}</div>}

      {!locked && (
        <div className="bnf-com-addrow" data-guide="splits-add">
          {vocab.other_roles.map((role) => (
            <Button key={role} size="sm" onClick={() => editor.change(model.addRow(draft, role))}>
              {vocab.add_labels[role]}
            </Button>
          ))}
        </div>
      )}

      <SplitPreview preview={shown} />

      {split.needs_primary && !editor.dirty && (
        <div className="bnf-com-nudge">
          Commission setup incomplete — pick the primary producer so the split is known before the first check.
        </div>
      )}

      {locked ? (
        <div className="bb-drop-meta">
          Only the {dealId ? "deal's" : "client's"} owner or someone with all commission access can change the split.
        </div>
      ) : (
        <div className="bnf-com-actions">
          {dealId && (
            <label className="bnf-com-scope" title={vocab.scope_hint}>
              Applies to
              <select className="bnf-intake-input" value={editor.scope} onChange={(event) => editor.setScope(event.target.value)}>
                {vocab.scopes.map((entry) => (
                  <option key={entry.key} value={entry.key}>
                    {entry.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          {editor.dirty && (
            <Button size="sm" onClick={editor.discard} disabled={editor.saving}>
              Discard
            </Button>
          )}
          <Button variant="primary" size="sm" onClick={editor.submit} disabled={!editor.dirty} busy={editor.saving}>
            {model.saveLabel({ scope: editor.scope, source: split.source, clientOnly: !dealId, saving: editor.saving })}
          </Button>
        </div>
      )}
    </div>
  );
}
