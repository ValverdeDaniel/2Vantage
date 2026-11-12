import { errorText } from '../lib/errors';
import Button from './Button';

/**
 * A failed request, shown where its data would be, with Try again (plan.md §8.22). The page form is the old load
 * error card (`card bnf-load-error`); `compact` is the old `error-message` line, for drawers and rows.
 *   error (any error; turned into text), title, onRetry, retrying (the button waits), compact
 */
export default function InlineError({ error, title = 'Could not load this.', onRetry, retrying = false, compact }) {
  const detail = error ? errorText(error) : '';
  const retry = onRetry && (
    <Button size="sm" onClick={onRetry} busy={retrying}>
      Try again
    </Button>
  );
  if (compact) {
    return (
      <div role="alert" className="error-message">
        {title}
        {detail && ` ${detail}`} {retry}
      </div>
    );
  }
  return (
    <div role="alert" className="card bnf-load-error">
      <div className="bb-tab-title">{title}</div>
      {detail && <p>{detail}</p>}
      {retry}
    </div>
  );
}
