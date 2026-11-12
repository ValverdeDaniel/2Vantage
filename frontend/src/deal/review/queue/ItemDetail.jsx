import { readyWords } from './queueWords';
import ValueChange from './ValueChange';

function when(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/*
 * The focused item's detail (old 891f1b3 `CensusClientReview.jsx` renderDetail, `ReadyWhy.jsx`): what we hold beside
 * what the client sent, a person the client added with what they gave for them, the carriers whose file needs the
 * column, and whose link it came through, when, and why it is ready. Threads and notes join with slice 56.
 */
export default function ItemDetail({ item }) {
  const at = when(item.at);
  return (
    <>
      {item.kind === 'person' ? (
        <>
          <div className="rr-hint">
            <span>ⓘ</span>A person the client added on their link: approve to add them to the census, or keep them off.
          </div>
          <dl className="rr-qi-sub">
            {(item.details || []).map((row) => (
              <div key={row.label}>
                <dt style={{ display: 'inline' }}>{row.label}: </dt>
                <dd style={{ display: 'inline', margin: 0 }}>{row.value}</dd>
              </div>
            ))}
          </dl>
        </>
      ) : (
        <ValueChange ours={item.ours} theirs={item.theirs} />
      )}
      {item.blocks?.length > 0 && (
        <div className="rr-hint rr-hint-warn">
          <span>⚠</span>
          {item.blocks.join(', ')} require{item.blocks.length === 1 ? 's' : ''} this column on their census file.
        </div>
      )}
      <div className="rr-qi-sub">
        {item.via === 'The client' ? 'Through the client link' : `Through ${item.via}'s link`}
        {at ? ` · ${at}` : ''} · {readyWords(item)}
      </div>
    </>
  );
}
