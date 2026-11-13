import ReqItem from './ReqItem';

/**
 * Documents carriers need (M57; old 891f1b3 `GetToMarketCard.jsx`): the renewal, the invoice and the claims, each with
 * ⬆ Attach, On file, ＋ Ask while missing, and Not needed / Still needed ▸ / Undo; a row reads Not needed on its own
 * when nothing is in force or shopped. The old custom asks and "＋ Add request" (M58, M59) wait: no app stores a
 * free-text ask yet.
 */
export default function DocumentsGroup({ dealId, group, writes, acceptOf }) {
  return group.items.map((item) => (
    <ReqItem key={item.key} dealId={dealId} item={item} writes={writes} accept={acceptOf(item.kind)} />
  ));
}
