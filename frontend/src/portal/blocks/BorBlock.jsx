/*
 * The Broker of Record signature (plan.md §8.20; L86, L97; OQ86). Ported from old Vantage 891f1b3
 * `BenefitsClientPortal.jsx` ("Authorizations & documents"): signed, or on file, or a typed full name that goes with
 * Save progress or Submit, never on its own (L97). The compliance files it used to carry are document slots here.
 */
export default function BorBlock({ bor, name, onName, readOnly }) {
  return (
    <div className="bb-portal-card" id="bnf-sec-bor">
      <div className="bb-panel-title">Authorizations &amp; documents</div>
      <div className="bb-panel-sub">The Broker of Record letter lets us work with carriers on your behalf.</div>
      {bor.signed ? (
        <div className="bnf-esign-done">
          <span className="bb-check">✓</span>
          <div className="bnf-esign-name">BOR signed by {bor.name}</div>
        </div>
      ) : bor.on_file ? (
        <div className="bnf-esign-done">
          <span className="bb-check">✓</span>
          <div className="bnf-esign-name">Broker of Record on file — nothing to sign</div>
        </div>
      ) : (
        <div className="form-group">
          <label htmlFor="bor-name">Sign the Broker of Record (type your full name)</label>
          <input
            id="bor-name"
            type="text"
            value={name}
            placeholder="Your full legal name"
            disabled={readOnly}
            onChange={(event) => onName(event.target.value)}
          />
        </div>
      )}
    </div>
  );
}
