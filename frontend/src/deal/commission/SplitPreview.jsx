import { formatMoney } from '../../lib/format';

/*
 * The live line under the split (H18; the old `bnf-com-preview`): "House 60.0% ($X) · producer pool 40% (first year,
 * firm default) · on $R expected", or that dollars wait for a premium. Every figure is the server's preview.
 */
export default function SplitPreview({ preview }) {
  const house = preview?.shares?.find((share) => share.role === 'house');
  const revenue = preview?.revenue;
  return (
    <div className="bnf-com-preview">
      <span>
        House <strong>{house ? house.pct_label : `${preview?.house_pct ?? '—'}%`}</strong>
        {house && house.amount != null ? ` (${formatMoney(house.amount)})` : ''}
        {' · '}producer pool <strong>{preview?.producer_pct ? `${preview.producer_pct}%` : '—'}</strong> (
        {preview?.year_label || 'first year'}
        {preview?.pct_source === 'default' ? ', firm default' : ''})
        {revenue != null ? ` · on ${formatMoney(revenue)} expected` : ' · dollars appear once a premium is known'}
      </span>
    </div>
  );
}
