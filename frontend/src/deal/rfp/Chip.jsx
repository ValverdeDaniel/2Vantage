import cx from '../../ui/cx';

/** One request chip (old CarriersTab.jsx `Chip` at 891f1b3): on when picked, dimmed and dashed when it does not fit. */
export default function Chip({ on, off, title, onClick, children }) {
  return (
    <button
      type="button"
      title={title}
      aria-pressed={Boolean(on)}
      className={cx('bnf-rfp-chip', on && 'bnf-rfp-chip-on', off && 'bnf-rfp-chip-off')}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
