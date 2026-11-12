import FieldInput from '../deal/shared/FieldInput';
import ConflictNote from './ConflictNote';
import FieldHelp from './FieldHelp';
import { fieldShown, intakeRef } from './portalModel';

/*
 * The intake questions a link asks, one card per section (plan.md §8.20; L83; B43). Ported from old Vantage 891f1b3
 * `BenefitsClientPortal.jsx` (the intake section cards): the label with the rose star when the deal needs it, "Where
 * do I find this?", the "we read" marker, a locked answer shown "Already on file ✓", a colleague's answer flagged,
 * and the conflict note. A question appears and goes as its rule passes over what they type (L83). The editor is the
 * shared FieldInput (intake, questionnaire and portal; O.4).
 *
 * bind: {values, set, conflicts, errors, keepTheirs, useMine, readOnly} from PortalForm.
 */
function Question({ field, bind }) {
  const ref = intakeRef(field.key);
  return (
    <div className="bb-portal-field">
      <label htmlFor={`q-${field.key}`}>
        {field.label}
        {field.needed && !field.locked && (
          <span className="bnf-qb-star" title="Needed to shop the market">
            *
          </span>
        )}
        {!field.locked && <FieldHelp text={field.help} />}
      </label>
      {field.we_read && !field.locked && (
        <div className="bnf-we-read">We read this from your documents — correct it if it is wrong.</div>
      )}
      {field.locked ? (
        <div className="bnf-portal-locked" title="Already on file">
          {field.value ? `${field.value} ` : 'Already on file '}
          <span className="bb-check">✓</span>
        </div>
      ) : (
        <FieldInput
          question={field}
          value={bind.values[ref]}
          disabled={bind.readOnly}
          label={field.label}
          onChange={(value) => bind.set(ref, value)}
        />
      )}
      {field.by_colleague && !field.locked && (
        <div className="bnf-portal-colleague">Updated by someone else on your team</div>
      )}
      {bind.errors[ref] && <div className="bnf-issue-line bb-rose">{bind.errors[ref]}</div>}
      <ConflictNote
        conflict={bind.conflicts[ref]}
        onKeep={() => bind.keepTheirs(ref)}
        onMine={() => bind.useMine(ref)}
      />
    </div>
  );
}

export default function IntakeSection({ intake, bind }) {
  return (intake?.sections || []).map((section, index) => {
    const shown = section.fields.filter((field) => fieldShown(field, bind.values));
    if (!shown.length) return null;
    return (
      <div key={section.key} id={index === 0 ? 'bnf-sec-intake' : undefined} className="bb-portal-card">
        <div className="bb-panel-title">{section.label}</div>
        <div className="bb-portal-fields">
          {shown.map((field) => (
            <Question key={field.key} field={field} bind={bind} />
          ))}
        </div>
      </div>
    );
  });
}
