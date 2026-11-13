import { useState } from 'react';
import { Link } from 'react-router';
import { useUpdateDeal } from '../../api/deals';
import { labelOf } from '../../api/meta';
import { useFactWrite } from '../../api/overview';
import { errorText } from '../../lib/errors';
import { formatMoney } from '../../lib/format';
import FactRow from '../../ui/FactRow';

// The question an intake answer row edits, from /api/meta/'s intake form (its hint and, for a choice, its options).
function question(meta, key) {
  for (const section of meta?.intake?.form?.sections || []) {
    const found = section.questions.find((q) => q.key === key);
    if (found) return found;
  }
  return {};
}

// The sentence a 400 gives for this fact (intake's {answers: {key: …}}, a door's {field: […]}), else the whole error.
function factError(error, key) {
  const data = error?.response?.data;
  const found = data?.answers?.[key] ?? data?.[key];
  return found ? [].concat(found).join(' ') : errorText(error);
}

// A typed deal size edits as plain dollars: '250000.00' → '250000'.
const sizeDraft = (value) => (value ? value.replace(/\.00$/, '') : '');

/**
 * The header's click-to-edit facts (M24–M30; old `ClientHeader.jsx`'s snapshot grid, in its order). Each writes
 * through its owner: intake's answers (Legal name, FEIN, SIC code, Situs state, Eligible employees; M25), intake's
 * coverage row for the medical incumbent while no current plan holds it (M26), the deal for the Agent of record and
 * the Potential deal size (M27, M29), the client's contacts for the main contact (M30; a first edit adds an HR admin).
 * The old Producer row is gone (M27); In-force commission is read-only (M28). A blank Legal name shows the client's
 * name, which is neither stored nor counted (M13, C9).
 */
export default function HeaderFacts({ deal, overview, meta }) {
  const { identity, facts } = overview;
  const write = useFactWrite(deal);
  const updateDeal = useUpdateDeal(deal.id);
  const [errors, setErrors] = useState({});
  const settle = (row) => ({
    onSuccess: () => setErrors((current) => ({ ...current, [row]: '' })),
    onError: (error) => setErrors((current) => ({ ...current, [row]: factError(error, row) })),
  });
  const answer = (key) => (value) => write.mutate({ kind: 'answer', key, value }, settle(key));
  const coverage = (key) => (value) =>
    write.mutate({ kind: 'coverage', key, value, coverageId: facts[key].coverage_id }, settle(key));
  const contact = (key) => (value) =>
    write.mutate({ kind: 'contact', key, value, contactId: facts.contact?.id }, settle(key));
  const dealFact = (key) => (value) => updateDeal.mutate({ [key]: value }, settle(key));
  const row = (key) => ({ onCommit: answer(key), value: facts[key], placeholder: question(meta, key).hint || '' });
  const states = (question(meta, 'situs_state').options || []).map((code) => ({ value: code, label: code }));
  const funding = (meta?.funding || []).map((option) => ({ value: option.key, label: option.label }));
  const fromPlans = (fact) =>
    fact.editable ? null : (
      <Link className="bnf-ov-row-hint" to={`/deals/${deal.id}/advisor?line=medical`}>
        from the current plan ↗
      </Link>
    );
  const agent = facts.agent_of_record;

  return (
    <div className="bnf-ov-facts">
      <div className="bnf-snapshot-grid">
        <FactRow
          label="Legal name"
          value={identity.legal_name}
          display={identity.legal_name || identity.legal_name_default}
          onCommit={answer('legal_name')}
          placeholder="Legal company name"
          error={errors.legal_name}
        />
        <FactRow label="FEIN" {...row('fein')} error={errors.fein} />
        <FactRow label="SIC code" {...row('sic_code')} error={errors.sic_code} />
        <FactRow
          label="Funding"
          value={facts.funding.value}
          display={labelOf(meta?.funding, facts.funding.value) || facts.funding.value}
          options={funding}
          readOnly={!facts.funding.editable}
          after={fromPlans(facts.funding)}
          onCommit={coverage('funding')}
          error={errors.funding}
        />
        <FactRow label="Situs state" {...row('situs_state')} options={states} error={errors.situs_state} />
        <FactRow
          label="Current carrier"
          value={facts.carrier.value}
          readOnly={!facts.carrier.editable}
          after={fromPlans(facts.carrier)}
          onCommit={coverage('carrier')}
          placeholder="Carrier"
          error={errors.carrier}
        />
        <FactRow label="Eligible employees" {...row('employee_count')} placeholder="#" error={errors.employee_count} />
        <FactRow
          label="Agent of record"
          hint="what carrier forms print; blank prints the owner, else the agency's producer"
          value={agent.value}
          display={agent.value || (agent.default ? <span className="bb-drop-meta">{agent.default} (default)</span> : '')}
          onCommit={dealFact('agent_of_record')}
          placeholder={agent.default || 'Agent name'}
          error={errors.agent_of_record}
        />
        {facts.in_force.length > 0 && (
          <FactRow
            label="In-force commission"
            hint="what the incumbents pay today — per line in the Commission panel"
            value={facts.in_force.map((line) => `${line.label} ${line.comp_label}`).join(' · ')}
            readOnly
          />
        )}
        <FactRow
          label="Potential deal size"
          value={sizeDraft(facts.deal_size)}
          display={formatMoney(facts.deal_size)}
          onCommit={dealFact('deal_size')}
          placeholder="$ amount"
          error={errors.deal_size}
        />
        <FactRow
          label="Contact"
          value={facts.contact?.name}
          onCommit={contact('name')}
          placeholder="Contact person"
          error={errors.name}
        />
        <FactRow
          label="Contact email"
          type="email"
          value={facts.contact?.email}
          onCommit={contact('email')}
          placeholder="name@company.com"
          error={errors.email}
        />
        <FactRow
          label="Contact phone"
          value={facts.contact?.phone}
          onCommit={contact('phone')}
          placeholder="(555) 555-0100"
          error={errors.phone}
        />
      </div>
    </div>
  );
}
