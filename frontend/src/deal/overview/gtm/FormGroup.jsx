import { Link } from 'react-router';
import { FormPicker } from '../../intake';
import { formLink, tabLink } from './gtmModel';
import ReqItem from './ReqItem';

/**
 * The medical questionnaire's and the stop-loss disclosure's groups (M50–M56, M108, M109; old 891f1b3
 * `GetToMarketCard.jsx`): the row with its form, who chose it and how far the answers are; the form picker, which is
 * intake's own (the questionnaire's choice door; locked once signed), hidden on a row that is not needed; the row's
 * controls (⬆ Attach, On file, Not needed / Still needed ▸ / Undo); Open questionnaire ▸ or Open disclosure ▸ once a
 * form is chosen; and the client's answers waiting with Review ▸ (slice 58 counts them; none until then). The
 * disclosure stays an "Optional" offer, with no controls, until a form is picked.
 */
export default function FormGroup({ deal, meta, group, writes, accept }) {
  const { item } = group;
  const link = formLink(deal.id, group);
  const live = !item.waived && !group.offer;
  return (
    <>
      <ReqItem
        dealId={deal.id}
        item={item}
        writes={writes}
        accept={accept}
        form
        wrap={false}
        after={
          live && link ? (
            <Link className="bnf-override-link" to={link.to}>
              {link.label}
            </Link>
          ) : null
        }
      >
        {!item.waived && <FormPicker deal={deal} meta={meta} item={item} />}
      </ReqItem>
      {group.pending_client > 0 && (
        <div className="bnf-req-line">
          <span className="bb-badge bb-badge-violet">Client</span>
          {group.pending_client} answer{group.pending_client === 1 ? '' : 's'} from the client to review
          <Link className="bnf-override-link" to={tabLink(deal.id, 'review')}>
            Review ▸
          </Link>
        </div>
      )}
    </>
  );
}
