import cx from '../../ui/cx';

/*
 * The coverage card's checkbox (old `CvgCheck`, 891f1b3): a button with role="checkbox", because it has a mixed state
 * (the select-all headers) and an asking tone (an unanswered line) that a native box cannot draw. `state` is 'on',
 * 'mixed' or ''.
 */
export default function CvgCheck({ state = '', disabled, title, label, onClick, tone = '' }) {
  const on = state === 'on';
  const mixed = state === 'mixed';
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={mixed ? 'mixed' : on}
      aria-label={label || title}
      className={cx('bnf-cvg-box', on && 'is-on', mixed && 'is-mixed', tone)}
      disabled={disabled}
      title={title || ''}
      onClick={onClick}
    />
  );
}
