import ReqItem from './ReqItem';

/**
 * Confirmations (M60; old 891f1b3 `GetToMarketCard.jsx`): COBRA, and salary and occupation when a life or disability
 * line is quoted, each "Confirmed" by a person's tick (the Census tab shows the same COBRA tick), with Not needed /
 * Still needed ▸ / Undo.
 */
export default function ConfirmGroup({ dealId, group, writes }) {
  return group.items.map((item) => <ReqItem key={item.key} dealId={dealId} item={item} writes={writes} accept="" />);
}
