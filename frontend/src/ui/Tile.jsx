import cx from './cx';

/*
 * One figure tile in the old look (H45, H116; 891f1b3 `CommissionsDashboard.jsx` Tile): a label, a value with an
 * optional tone (bb-green, bb-amber, bb-rose), muted when not built yet, an optional line under it and a title.
 */
export default function Tile({ label, value, tone = '', muted = false, title, sub = null }) {
  return (
    <div className="bb-stat-card" title={title}>
      <div className="bb-stat-label">{label}</div>
      <div className={cx('bb-stat-value', tone, muted && 'bnf-com-muted')}>{value}</div>
      {sub && <div className="bb-stat-sub">{sub}</div>}
    </div>
  );
}
