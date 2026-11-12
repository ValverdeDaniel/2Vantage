/*
 * What came back, by group, in the queue's header (old 891f1b3 `reviewrequest/ReviewGroupChips.jsx`; L16, U3d):
 *   By column  Everything 3 · ZIP · Changed 2 [Approve all 2 ✓] · Salary · Filled in 1
 * `groups`: [{key, label, sub, count}]; `active`: the picked key or null (Everything); `approve`: the picked group's
 * {label, onClick, disabled} or null. Nothing renders with no groups.
 */
export default function GroupChips({ groups = [], active = null, onPick, allCount, approve = null, label = '' }) {
  if (!groups.length) return null;
  return (
    <div className="rr-groups">
      {label && <span className="rr-groups-label">{label}</span>}
      <button
        type="button"
        className={`rr-chip${active == null ? ' rr-chip-on' : ''}`}
        aria-pressed={active == null}
        title="Show every item, whatever its group"
        onClick={() => onPick(null)}
      >
        Everything{typeof allCount === 'number' && <span>{allCount}</span>}
      </button>
      {groups.map((group) => {
        const on = active === group.key;
        return (
          <span key={group.key} className={`rr-group${on ? ' rr-group-on' : ''}`}>
            <button
              type="button"
              className={`rr-chip${on ? ' rr-chip-on' : ''}`}
              aria-pressed={on}
              title={`Show only ${group.label} (${group.count})`}
              onClick={() => onPick(group.key)}
            >
              {group.label}
              {group.sub && <i className="rr-group-sub"> · {group.sub}</i>}
              <span>{group.count}</span>
            </button>
            {on && approve && (
              <button
                type="button"
                className="btn btn-violet btn-sm rr-group-approve"
                disabled={Boolean(approve.disabled)}
                title={`${approve.label}: accept every item in ${group.label} as it stands, in one go`}
                onClick={approve.onClick}
              >
                {approve.label}
              </button>
            )}
          </span>
        );
      })}
    </div>
  );
}
