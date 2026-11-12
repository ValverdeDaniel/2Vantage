import { affixes, multiParts, toggleOption } from './fieldValue';

/*
 * One typed answer's editor (plan.md §4.5, §5.2; B3; O.4: shared by intake, the questionnaire and the portal). Ported
 * from old Vantage 891f1b3 `market/IntakeField.jsx`, in its markup and classes: a choice or Yes/No is a select, a
 * date a date input, a number a numeric input with its $ or % affix, text a text input (a long answer a textarea),
 * and a multi its option chips. A multi also takes typed text ("FL, GA") so it fills by keyboard; its chips follow
 * the text, and a chip click edits the text without taking the focus. The value is always the editor's text; the
 * caller saves it, and the server's one cleaner stores or refuses it.
 *
 * question: {type, options, hint, limit} · value: text · onChange(text) · onBlur · disabled · autoFocus · label
 */
export default function FieldInput({ question, value, onChange, onBlur, disabled = false, autoFocus = false, label }) {
  const type = question.type;
  const options = question.options || [];
  const common = { disabled, autoFocus, onBlur: onBlur || undefined, 'aria-label': label || question.label };
  const text = value ?? '';

  if (type === 'choice' || type === 'yesno') {
    const choices = type === 'yesno' ? ['Yes', 'No'] : options;
    return (
      <select className="bnf-intake-input" value={text} onChange={(event) => onChange(event.target.value)} {...common}>
        <option value="">Select…</option>
        {choices.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }

  if (type === 'multi') {
    const { picked } = multiParts(text, options);
    return (
      <>
        <input
          type="text"
          className="bnf-intake-input"
          value={text}
          placeholder={question.hint || 'Type them, or click below'}
          onChange={(event) => onChange(event.target.value)}
          {...common}
        />
        <div className="bnf-multi-chips">
          {options.map((option) => (
            <span
              key={option}
              className={`bnf-chip ${picked.includes(option) ? 'bnf-chip-on' : ''}`}
              onMouseDown={(event) => event.preventDefault()} // the typed text keeps the focus
              onClick={() => !disabled && onChange(toggleOption(text, option, options))}
            >
              {option}
            </span>
          ))}
        </div>
      </>
    );
  }

  if (type === 'date') {
    return (
      <input type="date" className="bnf-intake-input" value={text} onChange={(event) => onChange(event.target.value)} {...common} />
    );
  }

  if (type === 'number' || type === 'money' || type === 'percent') {
    const { before, after } = affixes(type);
    return (
      <div className="bnf-intake-numwrap">
        {before && <span className="bnf-intake-affix">{before}</span>}
        <input
          type="text"
          inputMode="decimal"
          className="bnf-intake-input"
          value={text}
          placeholder={question.hint}
          onChange={(event) => onChange(event.target.value)}
          {...common}
        />
        {after && <span className="bnf-intake-affix">{after}</span>}
      </div>
    );
  }

  if (question.limit) {
    return (
      <textarea
        className="bnf-intake-input"
        rows={3}
        maxLength={question.limit}
        value={text}
        placeholder={question.hint}
        onChange={(event) => onChange(event.target.value)}
        {...common}
      />
    );
  }

  return (
    <input
      type="text"
      className="bnf-intake-input"
      value={text}
      placeholder={question.hint}
      onChange={(event) => onChange(event.target.value)}
      {...common}
    />
  );
}
