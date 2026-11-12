import cx from './cx';

// The old badge tones (bb-badge-*); the text carries the meaning, the colour only reinforces it.
const TONES = {
  neutral: 'bb-badge-gray',
  muted: 'bb-badge-muted',
  brand: 'bb-badge-violet',
  info: 'bb-badge-violet',
  success: 'bb-badge-green',
  warning: 'bb-badge-amber',
  danger: 'bb-badge-rose',
};

/** A short label on the old `bb-badge`. tone: neutral | muted | brand | info | success | warning | danger. */
export default function Badge({ tone = 'neutral', icon, children, className, ...rest }) {
  return (
    <span className={cx('bb-badge', TONES[tone] || TONES.neutral, className)} {...rest}>
      {icon && <span aria-hidden="true">{icon} </span>}
      {children}
    </span>
  );
}
