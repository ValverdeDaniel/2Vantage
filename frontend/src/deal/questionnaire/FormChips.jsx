/*
 * The form chips (G7, G35): every form the deal arms, then any form already started, so a signed form keeps a way in.
 * Shown when there are two or more; a click writes `?form=`.
 */
export default function FormChips({ forms, active, onPick }) {
  if (forms.length < 2) return null;
  return (
    <div className="bb-acord-picker bnf-q-formchips">
      {forms.map((form) => (
        <button
          key={form.key}
          type="button"
          className={`bb-acord-chip ${form.key === active ? 'active' : ''}`}
          onClick={() => onPick(form.key)}
        >
          {form.label}
        </button>
      ))}
    </div>
  );
}
