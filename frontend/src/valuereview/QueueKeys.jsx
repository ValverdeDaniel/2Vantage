import { moreKeys } from './queueModel';

const Kbd = ({ k }) => <kbd className="rr-kbd">{k}</kbd>;

/*
 * The queue's key legend (L15; old 891f1b3 `ReviewQueue.jsx` `rr-queue-keys`): A · X · R · ↑↓ always, in the focused
 * item's own words, and "?" for every other key it takes. A blocked X greys and says why on hover.
 */
export default function QueueKeys({ item, cfg, keyLabels, readOnly, open, onToggle }) {
  const legendA = (item && cfg.approve) || keyLabels.a;
  const legendX = (item && cfg.reject) || keyLabels.x;
  return (
    <div className="rr-queue-keys">
      <span>
        <Kbd k="A" /> {legendA}
      </span>
      <span
        className={item && cfg.rejectBlocked ? 'rr-queue-key-off' : undefined}
        title={(item && cfg.rejectBlocked) || undefined}
      >
        <Kbd k="X" /> {legendX}
      </span>
      <span>
        <Kbd k="R" /> {keyLabels.r}
      </span>
      <span>
        <Kbd k="↑" />
        <Kbd k="↓" /> move
      </span>
      <button
        type="button"
        className={`rr-queue-keys-more${open ? ' rr-queue-keys-more-on' : ''}`}
        aria-expanded={open}
        title="Every key this item takes"
        onClick={onToggle}
      >
        ?
      </button>
      {open && (
        <div className="rr-queue-keys-all">
          {moreKeys(cfg, readOnly).map(([key, label]) => (
            <span key={key}>
              <Kbd k={key} /> {label}
            </span>
          ))}
          <span>
            <Kbd k="?" /> these keys
          </span>
        </div>
      )}
    </div>
  );
}

export { Kbd };
