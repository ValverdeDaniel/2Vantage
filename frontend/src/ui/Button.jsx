import styles from './Button.module.css';
import cx from './cx';
import Spinner from './Spinner';

/**
 * variant: 'primary' | 'secondary' | 'danger' | 'ghost' · size: 'sm' | 'md' · busy: shows a spinner and disables.
 * `as` renders another element or component with button styling (e.g. as={Link} to="/"); type defaults to "button".
 */
export default function Button({
  variant = 'secondary',
  size = 'md',
  busy = false,
  block = false,
  as: Component = 'button',
  type,
  disabled,
  className,
  children,
  ...rest
}) {
  const isButton = Component === 'button';
  return (
    <Component
      type={isButton ? type || 'button' : type}
      className={cx(styles.button, styles[variant], styles[size], block && styles.block, className)}
      disabled={isButton ? disabled || busy : undefined}
      aria-disabled={!isButton && disabled ? true : undefined}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy && <Spinner size="sm" label="" />}
      {children}
    </Component>
  );
}
