import cx from '../../../ui/cx';
import { SelectAllBox } from './cells';

/*
 * A column head of the rows board (plan.md §8.14; F32, F57): a sortable column sorts on a click (or Enter) and flips
 * on a second, showing ▲ or ▼; the ☐ column's head is the select-all box.
 */
export default function HeadCell({ col, ui }) {
  if (col.kind === 'select') {
    return (
      <th scope="col">
        <SelectAllBox ids={ui.ticks.selectable} ticked={ui.ticks.ids} editing={ui.editing} onChange={ui.ticks.setMany} />
      </th>
    );
  }
  if (!col.sortable) {
    return <th scope="col">{col.label}</th>;
  }
  const on = ui.sort.key === col.key;
  return (
    <th
      scope="col"
      className={cx('bnf-sortable', on && 'bnf-sorted')}
      aria-sort={on ? (ui.sort.dir === 1 ? 'ascending' : 'descending') : undefined}
      tabIndex={0}
      onClick={() => ui.sortBy(col.key)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          ui.sortBy(col.key);
        }
      }}
    >
      {col.label}
      {on && <span className="bnf-sort-arrow">{ui.sort.dir === 1 ? '▲' : '▼'}</span>}
    </th>
  );
}
