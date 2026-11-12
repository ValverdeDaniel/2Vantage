import { progressBadge } from './formModel';

/*
 * The form's header (G38, G42): its title and subtitle, "N% complete" (amber, then green) from the server, "Saving…",
 * and the Form view / Table view toggle. The ⬇ menu comes with the PDFs (G56, slice 43).
 */
export default function Toolbar({ spec, progress, saving, layout, onLayout }) {
  const badge = progressBadge(progress);
  return (
    <div className="bnf-q-toolbar">
      <div>
        <h2 className="bnf-q-title">{spec.title}</h2>
        <p className="bnf-q-subtitle">{spec.subtitle}</p>
      </div>
      <div className="bnf-q-actions">
        <span className={`bb-badge ${badge.tone}`}>{badge.text}</span>
        {saving && <span className="bnf-q-saving">Saving…</span>}
        <div className="bb-acord-viewtoggle">
          <button type="button" className={layout === 'form' ? 'active' : ''} onClick={() => onLayout('form')}>
            Form view
          </button>
          <button type="button" className={layout === 'table' ? 'active' : ''} onClick={() => onLayout('table')}>
            Table view
          </button>
        </div>
      </div>
    </div>
  );
}
