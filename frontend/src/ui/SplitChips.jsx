import { formatMoney } from '../lib/format';

/*
 * Who gets what, inline (H51, H116; 891f1b3 `BookTab.jsx` SplitChips): "Primary Dana 40% · Referral Riverside 6%",
 * the house first when shown. Every figure is the server's (`pct_label`, `amount`); the own tier gets its own share only.
 */
export default function SplitChips({ shares, showHouse = true, showMoney = false }) {
  const shown = (shares || []).filter((share) => showHouse || share.role !== 'house');
  if (!shown.length) return <span className="bb-empty">house</span>;
  return (
    <span className="bnf-com-chips">
      {shown.map((share) => (
        <span
          key={`${share.role}-${share.party ?? 'house'}`}
          className={`bnf-com-chip bnf-com-role-${share.role}`}
          title={`${share.role_label} · ${share.name} · ${share.pct_label}${share.amount != null ? ` · ${formatMoney(share.amount)}` : ''}`}
        >
          <span className="bnf-com-chip-role">{share.role_label}</span>
          {share.role !== 'house' ? ` ${share.name}` : ''}
          <span className="bnf-com-chip-pct"> {share.pct_label}</span>
          {showMoney && share.amount != null ? (
            <span className="bnf-com-chip-money"> {formatMoney(share.amount)}</span>
          ) : null}
        </span>
      ))}
    </span>
  );
}
