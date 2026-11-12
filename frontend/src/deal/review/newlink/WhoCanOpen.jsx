/*
 * Who can open it (L64, OQ80; old 891f1b3 `LinkSettingsCard.jsx` `WhoCanOpen`): a private link or a PIN. The server's
 * dry run names the lowest level what is ticked allows and what set it, so a level too low is greyed out saying what
 * to untick, and a new link rises to its floor by itself. Words from /api/meta/ `review.levels`.
 */
export default function WhoCanOpen({ meta, security, floor, onChange, disabled }) {
  const levels = meta?.levels || []; // weakest first
  const rank = (key) => levels.findIndex((item) => item.key === key);
  const lowest = floor?.level || levels[0]?.key;
  const because = (floor?.because || []).join(' and ');
  const needs = meta?.level_needs?.[lowest] || '';
  const level = rank(security) >= rank(lowest) ? security : lowest;
  return (
    <div className="rr-newlink-levels" role="radiogroup" aria-label="Who can open it">
      {levels.map((item) => {
        const below = rank(item.key) < rank(lowest);
        const note = below ? `${because} needs at least ${needs}. Untick ${because} to pick this.` : item.means;
        return (
          <label key={item.key} className={`rr-edit-level${below ? ' rr-edit-level-off' : ''}`} title={note}>
            <input type="radio" name="newlink-access" checked={level === item.key} disabled={disabled || below}
              onChange={() => onChange({ security: item.key })} />
            <span>
              <b>{item.label}</b>
              {level === item.key || below ? ` ${note}` : ''}
            </span>
          </label>
        );
      })}
      {level === 'pin' && (
        <div className="rr-edit-note">
          The app makes a 6-digit PIN for each person&rsquo;s link and shows it to you once. You give it to them yourself.
        </div>
      )}
      {rank(security) < rank(level) && because && <div className="rr-edit-note">Raised to {needs} because of {because}.</div>}
    </div>
  );
}
