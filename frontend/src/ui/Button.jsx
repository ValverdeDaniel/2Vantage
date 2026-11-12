import cx from './cx';

// The old buttons (App.css): .btn with a variant, .btn-sm for the small size. A "ghost" is the old secondary.
const VARIANTS = { primary: 'btn-primary', secondary: 'btn-secondary', ghost: 'btn-secondary', danger: 'btn-danger' };

/**
 * variant: 'primary' | 'secondary' | 'ghost' | 'danger' · size: 'sm' | 'md' · busy: disabled while a request runs.
 * `as` renders another element or component with button styling (e.g. as={Link} to="/"); type defaults to "button".
 * `block` spans the row (bb-full-width).
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
      className={cx(
        'btn',
        VARIANTS[variant] || VARIANTS.secondary,
        size === 'sm' && 'btn-sm',
        block && 'bb-full-width',
        className,
      )}
      disabled={isButton ? disabled || busy : undefined}
      aria-disabled={!isButton && disabled ? true : undefined}
      aria-busy={busy || undefined}
      {...rest}
    >
      {children}
    </Component>
  );
}
