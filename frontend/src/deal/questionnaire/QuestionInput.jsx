import { memo, useMemo } from 'react';
import FieldInput from '../shared/FieldInput';

/*
 * One question's input on the Form and the Table alike (G39), so both store the same strings: the shared FieldInput
 * (text, date, number, money, percent, choice, Yes/No). A picker's options are its own list or its row's slice of a
 * dependent table, by the option key the server sent (G12). Memoised, so typing in one box never re-renders the
 * other pickers — the SIC lists hold a thousand options each and are built once (G17).
 */
function QuestionInput({ slot, field, options, value, onChange, disabled }) {
  const question = useMemo(
    () => ({ type: field.type, options, hint: field.hint, label: field.label }),
    [field, options],
  );
  return <FieldInput question={question} value={value} onChange={(next) => onChange(slot, next)} disabled={disabled} />;
}

export default memo(QuestionInput);
