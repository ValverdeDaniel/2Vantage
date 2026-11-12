/*
 * What we hold → what came in, side by side (old 891f1b3 `reviewrequest/ValueChange.jsx`; D-140). A blank side says
 * "blank" rather than nothing, so a filled-in value and a cleared one read differently at a glance. A block (contacts,
 * coverage, lines) is a list: one line each.
 */
function Value({ value }) {
  if (Array.isArray(value)) {
    if (!value.length) return <i className="rr-change-blank">blank</i>;
    return (
      <span className="rr-change-value">
        {value.map((line, index) => (
          <span key={`${index}-${line}`} style={{ display: 'block' }}>
            {line}
          </span>
        ))}
      </span>
    );
  }
  if (value === '' || value == null) return <i className="rr-change-blank">blank</i>;
  return <span className="rr-change-value">{String(value)}</span>;
}

function Side({ label, value, className }) {
  return (
    <div className={`rr-change-side ${className}`}>
      <span className="rr-change-label">{label}</span>
      <Value value={value} />
    </div>
  );
}

export default function ValueChange({ ours, theirs, oursLabel = 'On file', theirsLabel = 'The client sent' }) {
  return (
    <div className="rr-change">
      <Side label={oursLabel} value={ours} className="rr-change-old" />
      <span className="rr-change-arrow" aria-hidden="true">
        →
      </span>
      <Side label={theirsLabel} value={theirs} className="rr-change-new" />
    </div>
  );
}
