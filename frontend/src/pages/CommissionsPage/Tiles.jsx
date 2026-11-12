import { formatMoney } from '../../lib/format';
import Tile from '../../ui/Tile';

/*
 * The tiles (H45; 891f1b3 `CommissionsDashboard.jsx`): Expected (annual), House share* and Producer pool* (the all
 * tier's), Next 12 months and Booked records, over the Book's current filters. Expected counts booked and active
 * records only (bug 5). Received YTD and Open gaps wait with the ledger (OQ6); "Owed to producers" is dropped (H46).
 */
export default function Tiles({ totals, isAll }) {
  const money = (value) => (totals && value != null ? formatMoney(value) : '—');
  return (
    <div className="bnf-com-tiles" data-guide="commissions-tiles">
      <Tile label="Expected (annual)" value={money(totals?.expected)} tone="bb-green" />
      {isAll && <Tile label="House share" value={money(totals?.house)} />}
      {isAll && <Tile label="Producer pool" value={money(totals?.pool)} />}
      <Tile
        label="Next 12 months"
        value={money(totals?.next_12)}
        title="Expected revenue from records in force over the next 12 months (expected ÷ 12 per month across each term)"
      />
      <Tile label="Booked records" value={totals ? totals.records : '—'} />
    </div>
  );
}
