import AskFoot from './AskFoot';
import AskParts from './AskParts';
import { itemState, STATE_CLASSES, STATE_WORDS, withColumn } from './askCardModel';
import { chipWords, STATUS_CLASSES } from './requestModel';

/** Whether the picked request's census scope asks this column now (its blanks, not one value at a time). */
function columnOnLink(target, key) {
  const { census, census_columns: columns } = target.parts;
  return !['none', 'selected', ''].includes(census) && (!columns.length || columns.includes(key));
}

/*
 * The ask list as the Ask card on one person's link (plan.md §8.8; L42; old 891f1b3 `RequestRail.jsx` `building`
 * link mode): each row says where it stands on THAT link, a tick drafts it for the request or takes it off, the part
 * switches stand above the list and Update link below it. `card` is `useAskCard`'s.
 */
export default function askMode({ card, target, meta, pane, labels, readOnly }) {
  const { change } = card;
  const names = target.names.join(', ') || 'the private link';
  return {
    title: 'Ask',
    sub: `What ${names} is asked. Ticks and what comes off wait for Update link: nothing reaches them before.`,
    top: <AskParts pane={pane} meta={meta} target={target} change={change} onChange={card.set} disabled={readOnly || card.busy} />,
    foot: <AskFoot card={card} target={target} meta={meta} readOnly={readOnly} />,
    tickOf(item) {
      const state = itemState(item, target, change);
      const mine = STATE_WORDS[state];
      return {
        checked: state === 'on_link' || state === 'will_add',
        enabled: true,
        chip: mine || chipWords(item, labels),
        cls: mine ? STATE_CLASSES[state] : STATUS_CLASSES[item.status] || '',
        undo: null,
      };
    },
    onTick: card.tick,
    toAsk(section) {
      return section.items
        .filter((item) => item.status === 'missing' && itemState(item, target, change) === 'missing')
        .map((item) => item.ref);
    },
    addAll: card.addAll,
    columnTickOf(column) {
      const onLink = columnOnLink(target, column.key);
      const off = change.off.columns.includes(column.key);
      const on = change.on.columns.includes(column.key);
      const chips = [];
      if (off) chips.push(['Coming off', 'rr-rail-chip-off']);
      else if (on) chips.push(['Will be added', 'rr-rail-chip-cart']);
      else if (onLink) chips.push(['On their link', 'rr-rail-chip-asked']);
      if (column.blank) chips.push([`${column.blank} blank`, '']);
      if (!chips.length) chips.push(['On file', 'rr-rail-chip-file']);
      return { checked: (onLink && !off) || on, enabled: onLink || Boolean(column.blank), chips };
    },
    onColumnTick: (column) => card.set((now) => withColumn(now, column.key, columnOnLink(target, column.key))),
  };
}
