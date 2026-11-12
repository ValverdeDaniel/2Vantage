import { FamilyBody, FamilyPills } from './FamilyControls';

/*
 * Rung 1 of the priced-version editor (plan.md §8.14; F76; the old DraftRowEditor): the family pills, that family's
 * compact inputs and a note, inside the draft row's Plan cell — the draft row IS the input. Type 5, Enter, done: Enter
 * in any input commits, Escape discards; ▾ docks the same editor above the table with room for which plans it applies
 * to and the version's name.
 */
export default function DraftRowEditor({ kit }) {
  const { draft, priced } = kit;
  const keys = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      kit.commit();
    }
    if (event.key === 'Escape') kit.cancel();
  };
  return (
    <div className="bnf-pv-inline">
      <FamilyPills
        priced={priced}
        family={draft.family}
        onFamily={kit.setFamily}
        anchorIsCurrent={kit.byId.get(draft.anchorId)?.role === 'current'}
        locked={Boolean(draft.editId)}
        compact
      />
      <FamilyBody kit={kit} compact onKeyDown={keys} />
      <div className="bnf-pv-inline-row">
        <input
          type="text"
          className="bnf-pv-inline-note"
          aria-label="Note"
          placeholder="note — per verbal conversation with the rep…"
          value={draft.note}
          onChange={(event) => kit.patch({ note: event.target.value })}
          onKeyDown={keys}
          disabled={kit.busy}
        />
        <button
          type="button"
          className="bnf-pv-inline-btn"
          title="More — which plans it applies to and the version’s name"
          onClick={() => kit.patch({ expanded: true })}
        >
          ▾
        </button>
        <button
          type="button"
          className="bnf-pv-inline-btn bnf-pv-inline-ok"
          title="Add this priced version (Enter)"
          aria-label="Add this priced version"
          onClick={kit.commit}
          disabled={kit.busy}
        >
          ✓
        </button>
        <button
          type="button"
          className="bnf-pv-inline-btn bnf-conc-remove"
          title="Discard the draft (Esc)"
          aria-label="Discard the draft"
          onClick={kit.cancel}
        >
          ✕
        </button>
      </div>
    </div>
  );
}
