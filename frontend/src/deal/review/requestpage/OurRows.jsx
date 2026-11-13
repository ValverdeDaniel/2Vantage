import { chipWords } from './requestModel';

const TONES = { question: 'q', in_cart: 'cart', answered: 'review', missing: 'missing' };

/*
 * Our form, in the middle of the request page with All people (plan.md §8.8; L30, L34; old 891f1b3 `RequestForm.jsx`):
 * one tab of the deal as we see it, a row per question — label · value · where it stands — built from the page's own
 * read, never a second one. Each row carries the same `data-ask-ref` as their page, so a click picks its card; a
 * double-click offers edit mode (L34). The census tab lists each column with its blanks, as the ask list counts them
 * (the roster stays on the Census tab).
 */
function Row({ item, labels, picked, onPick, onEdit }) {
  const words = chipWords(item, labels);
  return (
    <div className={`rr-fr${picked ? ' rr-rail-q-on' : ''}`} data-ask-ref={item.ref} role="button" tabIndex={0} onClick={() => onPick(item.ref)}
      onKeyDown={(event) => event.key === 'Enter' && onPick(item.ref)} onDoubleClick={() => onEdit(item)}
      title="A click opens its card; a double-click types in their answer (edit mode)">
      <div className="rr-fr-label">
        {item.label}
        {item.needed && (
          <i className="rr-rail-req" title="Required">
            *
          </i>
        )}
      </div>
      <div className="rr-fr-value">{item.value ? <span>{item.value}</span> : <span className="rr-fr-blank">blank</span>}</div>
      <div className="rr-fr-status">
        {words && <span className={`rr-fr-chip rr-fr-chip-${TONES[item.status] || 'saved'}`}>{words}</span>}
        {!words && <span className="rr-fr-chip rr-fr-chip-missing">{labels?.missing || 'Missing'}</span>}
      </div>
    </div>
  );
}

export default function OurRows({ page, labels, picked, onPick, onEdit }) {
  const sections = [];
  page.items.forEach((item) => {
    const last = sections[sections.length - 1];
    if (last && last.label === item.section) last.items.push(item);
    else sections.push({ label: item.section, items: [item] });
  });
  return (
    <div className="rr-form" aria-label="Our form">
      <div className="rr-reqpage-colhead">
        <b>Our form</b>
        <span className="rr-edit-note"> · this tab as we hold it. Double-click a row to type in an answer.</span>
      </div>
      {sections.map((section) => (
        <div key={section.label} className="rr-form-sec">
          <div className="rr-form-sechead">{section.label}</div>
          {section.items.map((item) => (
            <Row key={item.ref} item={item} labels={labels} picked={picked === item.ref} onPick={onPick} onEdit={onEdit} />
          ))}
        </div>
      ))}
      {page.columns && (
        <div className="rr-form-sec rr-form-census">
          <div className="rr-form-sechead">Census columns</div>
          <table className="rr-census-table">
            <tbody>
              {page.columns.map((column) => (
                <tr key={column.key} className={column.required_blank ? 'rr-census-open' : ''}>
                  <td>{column.label}</td>
                  <td className="rr-census-type">{column.required ? 'required' : ''}</td>
                  <td>{column.blank ? `${column.blank} blank` : 'on file'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
