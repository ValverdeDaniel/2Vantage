import { holdWords } from './questionnaireModel';

/*
 * The company officer's typed signature on the client's page (plan.md §8.20; G93, G55, L91; slice 58). Ported from old
 * Vantage 891f1b3 `BenefitsClientPortal.jsx` (`bnf-q-signform`): what the signature attests (the form's own signature
 * text), the sign line by the kind of form, the name box, and — when blank required answers held the last try — "Not
 * signed yet — N required answers are still blank. Sign anyway, as it is." The name rides Save or Submit, after the
 * answers (the server signs what the client's own answers say, G51).
 *
 * sign: {label, attestation} · name · onName(text) · hold: {filled, total} | undefined · anyway · onAnyway(bool)
 */
export default function QuestionnaireSign({ sign, name, onName, hold, anyway, onAnyway, readOnly }) {
  return (
    <div className="bnf-q-signform">
      {sign.attestation && <p className="bnf-q-intro bnf-q-attestation">{sign.attestation}</p>}
      <label className="bnf-q-label">
        {sign.label}
        <input
          className="bnf-intake-input"
          value={name || ''}
          placeholder="Full name"
          disabled={readOnly}
          aria-label="Your full name, to sign"
          onChange={(event) => onName(event.target.value)}
        />
      </label>
      {hold && (
        <label className="bnf-q-signhold bnf-q-signanyway">
          <input type="checkbox" checked={Boolean(anyway)} disabled={readOnly} onChange={(e) => onAnyway(e.target.checked)} />{' '}
          {holdWords(hold)} Sign anyway, as it is.
        </label>
      )}
    </div>
  );
}
