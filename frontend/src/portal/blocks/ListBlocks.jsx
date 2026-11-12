import ConflictNote from '../ConflictNote';
import { blockRef } from '../portalModel';

/*
 * The intake's list blocks (plan.md §8.20; L85; OQ84): Contacts ("Who should we work with?") and Current coverage
 * ("What do you have in place today?"). Ported from old Vantage 891f1b3 `BenefitsClientPortal.jsx` in markup, classes
 * (`bnf-subcard`, `bnf-subcard-row`, `bnf-intake-input`) and words. Each list is one answer that waits for a person
 * (OQ84): what they type here never lands on the deal by itself. A new row carries its own key until it is saved.
 */
function newKey() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  return `k${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
}

function useRows(block, bind) {
  const ref = blockRef(block);
  const rows = bind.values[ref] || [];
  const put = (index, key, value) => bind.set(ref, rows.map((row, i) => (i === index ? { ...row, [key]: value } : row)));
  const add = (row) => bind.set(ref, [...rows, { ...row, client_key: newKey() }]);
  return { ref, rows, put, add };
}

function Note({ ref_, bind }) {
  return (
    <>
      {bind.errors[ref_] && <div className="bnf-issue-line bb-rose">{bind.errors[ref_]}</div>}
      <ConflictNote
        conflict={bind.conflicts[ref_]}
        onKeep={() => bind.keepTheirs(ref_)}
        onMine={() => bind.useMine(ref_)}
      />
    </>
  );
}

export function ContactsBlock({ block, bind }) {
  const { ref, rows, put, add } = useRows('contacts', bind);
  const off = bind.readOnly;
  return (
    <div className="bb-portal-card" id="bnf-sec-contacts">
      <div className="bb-panel-title">Contacts</div>
      <div className="bb-panel-sub">Who should we work with?</div>
      {rows.map((contact, index) => (
        <div key={contact.client_key ?? contact.id ?? `new-${index}`} className="bnf-subcard">
          <div className="bnf-subcard-row">
            <select
              className="bnf-intake-input bnf-w-narrow"
              aria-label="Role"
              value={contact.role || ''}
              disabled={off}
              onChange={(event) => put(index, 'role', event.target.value)}
            >
              {block.roles.map((role) => (
                <option key={role.key} value={role.key}>
                  {role.label}
                </option>
              ))}
            </select>
            <input className="bnf-intake-input" aria-label="Name" placeholder="Name" value={contact.name || ''}
                   disabled={off} onChange={(event) => put(index, 'name', event.target.value)} />
          </div>
          <div className="bnf-subcard-row">
            <input className="bnf-intake-input" aria-label="Title" placeholder="Title" value={contact.title || ''}
                   disabled={off} onChange={(event) => put(index, 'title', event.target.value)} />
            <input className="bnf-intake-input" aria-label="Email" placeholder="Email" type="email"
                   value={contact.email || ''} disabled={off}
                   onChange={(event) => put(index, 'email', event.target.value)} />
            <input className="bnf-intake-input bnf-w-narrow" aria-label="Phone" placeholder="Phone" type="tel"
                   value={contact.phone || ''} disabled={off}
                   onChange={(event) => put(index, 'phone', event.target.value)} />
          </div>
        </div>
      ))}
      <button type="button" className="btn btn-secondary btn-sm" disabled={off}
              onClick={() => add({ role: 'hr_admin', name: '', title: '', email: '', phone: '' })}>
        ＋ Add contact
      </button>
      <Note ref_={ref} bind={bind} />
    </div>
  );
}

export function CoverageBlock({ block, bind }) {
  const { ref, rows, put, add } = useRows('coverage', bind);
  const off = bind.readOnly;
  return (
    <div className="bb-portal-card" id="bnf-sec-coverage">
      <div className="bb-panel-title">Current coverage</div>
      <div className="bb-panel-sub">What do you have in place today?</div>
      {rows.map((line, index) => (
        <div key={line.client_key ?? line.id ?? `new-${index}`} className="bnf-subcard">
          <div className="bnf-subcard-row">
            <select className="bnf-intake-input bnf-w-narrow" aria-label="Line of coverage" value={line.line || ''}
                    disabled={off} onChange={(event) => put(index, 'line', event.target.value)}>
              {block.lines.map((option) => (
                <option key={option.key} value={option.key}>
                  {option.label}
                </option>
              ))}
            </select>
            <input className="bnf-intake-input" aria-label="Carrier" placeholder="Carrier" value={line.carrier || ''}
                   disabled={off} onChange={(event) => put(index, 'carrier', event.target.value)} />
          </div>
          <div className="bnf-subcard-row">
            <select className="bnf-intake-input bnf-w-narrow" aria-label="Funding" value={line.funding || ''}
                    disabled={off} onChange={(event) => put(index, 'funding', event.target.value)}>
              <option value="">Funding…</option>
              {block.funding.map((option) => (
                <option key={option.key} value={option.key}>
                  {option.label}
                </option>
              ))}
            </select>
            <input type="date" className="bnf-intake-input bnf-w-narrow" title="Renewal date" aria-label="Renewal date"
                   value={line.renewal_date || ''} disabled={off}
                   onChange={(event) => put(index, 'renewal_date', event.target.value)} />
          </div>
        </div>
      ))}
      <button type="button" className="btn btn-secondary btn-sm" disabled={off}
              onClick={() => add({ line: 'medical', carrier: '', funding: '', renewal_date: '' })}>
        ＋ Add coverage line
      </button>
      <Note ref_={ref} bind={bind} />
    </div>
  );
}

export function LinesBlock({ block, bind }) {
  const ref = blockRef('lines');
  const picked = bind.values[ref] || [];
  const toggle = (key) =>
    bind.set(ref, picked.includes(key) ? picked.filter((one) => one !== key) : [...picked, key]);
  return (
    <div className="bb-portal-card" id="bnf-sec-lines">
      <div className="bb-panel-title">Coverage you’d like quoted</div>
      <div className="bb-panel-sub">Check everything you want us to shop</div>
      <div className="bnf-multi-chips">
        {block.lines.map((line) => (
          <span
            key={line.key}
            role="checkbox"
            aria-checked={picked.includes(line.key)}
            tabIndex={0}
            className={`bnf-chip ${picked.includes(line.key) ? 'bnf-chip-on' : ''}`}
            onClick={() => !bind.readOnly && toggle(line.key)}
            onKeyDown={(event) => event.key === ' ' && !bind.readOnly && toggle(line.key)}
          >
            {line.label}
          </span>
        ))}
      </div>
      {block.note && <div className="bb-drop-meta">{block.note}</div>}
      <Note ref_={ref} bind={bind} />
    </div>
  );
}
