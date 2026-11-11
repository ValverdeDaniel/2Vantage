import TextInput from './TextInput';

/**
 * The browser's date picker. `value` and the change event's value are 'YYYY-MM-DD' or ''.
 * onValueChange(value) is a shortcut for onChange={(e) => …(e.target.value)}.
 */
export default function DateInput({ value, onChange, onValueChange, ...rest }) {
  return (
    <TextInput
      type="date"
      value={value ?? ''}
      onChange={(event) => {
        onChange?.(event);
        onValueChange?.(event.target.value);
      }}
      {...rest}
    />
  );
}
