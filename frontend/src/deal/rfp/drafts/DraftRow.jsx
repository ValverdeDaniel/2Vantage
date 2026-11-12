import cx from '../../../ui/cx';
import { toWords } from './draftsModel';

/*
 * One email draft (plan.md §9.11; K58–K66; old CarriersTab.jsx CarrierDrafts at 891f1b3): To (the label, the address
 * or "your rep", and who is copied), Subject, what is attached, Copy and "Open in Outlook ⬇" (an `.eml` Outlook opens
 * as an unsent draft, checked before it downloads, K63), and the Sent tick with its date, "Nov 11" (K64, K65). What
 * changed since a send is said under the subject (G113).
 */
export default function DraftRow({ draft, files, sending, onCopy, onSent }) {
  const sent = Boolean(draft.sent);
  const eml = `draft-${draft.key}`;
  const by = sent && draft.sent.by ? ` by ${draft.sent.by}` : '';
  return (
    <tr data-guide={`rfp-draft-${draft.key}`} className={cx(sent && 'bnf-rfp-row-in')}>
      <td>
        <div className="bnf-rfp-doc">{draft.label}</div>
        <div className="bnf-rfp-sub">{toWords(draft)}</div>
      </td>
      <td className="bnf-rfp-sub">
        {draft.subject}
        {(draft.changed || []).map((text) => (
          <div key={text} className="bnf-rfp-rownote bb-amber">
            ⚠ {text}
          </div>
        ))}
      </td>
      <td className="bnf-rfp-sub">{draft.attachments.length ? draft.attachments.join(' · ') : 'Nothing ticked'}</td>
      <td className="bnf-rfp-draft-actions">
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          title="The subject and the email text, to paste into your own email"
          onClick={() => onCopy(draft)}
        >
          Copy
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={files.busy === eml}
          title="An .eml file Outlook opens as an unsent draft, attachments included"
          onClick={() => files.download(eml, `${draft.name} email`)}
        >
          {files.busy === eml ? 'Building…' : 'Open in Outlook ⬇'}
        </button>
      </td>
      <td className="bnf-rfp-draft-sent">
        <label title={sent ? `Marked sent${by}` : 'Tick once you have sent it'}>
          <input
            type="checkbox"
            checked={sent}
            disabled={sending}
            aria-label={`${draft.label} sent`}
            onChange={(event) => onSent(draft.key, event.target.checked)}
          />
          {sent ? ` ${draft.sent.shown}` : ''}
        </label>
      </td>
    </tr>
  );
}
