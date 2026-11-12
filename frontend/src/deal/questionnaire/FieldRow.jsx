import { optionsFor } from './formModel';
import QuestionInput from './QuestionInput';

/*
 * One question on the paper layout (G36): the label with its red star, the input, the italic hint. `data-q-slot` names
 * the answer, which Enter and Tab walk (G41).
 */
export default function FieldRow({ spec, field, slot, data, value, onChange, disabled }) {
  return (
    <div className={`bnf-q-field bnf-q-w${field.width || 1}`} data-q-slot={slot}>
      <label className="bnf-q-label">
        {field.label}
        {field.required && <span className="bnf-q-req">*</span>}
      </label>
      <QuestionInput
        slot={slot}
        field={field}
        options={optionsFor(spec, field, data.options?.[slot])}
        value={value}
        onChange={onChange}
        disabled={disabled}
      />
      {field.hint && <div className="bnf-q-hint">{field.hint}</div>}
    </div>
  );
}
