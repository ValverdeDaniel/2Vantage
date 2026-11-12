import { previewWords } from './lensModel';

/*
 * Exactly what the carrier receives (plan.md §8.12; K87; old CensusFormatLens.jsx at 891f1b3): the first rows from the
 * same builder the download and the packet run, a required blank highlighted, with the legend.
 */
export default function LensPreview({ carrier, preview }) {
  const missing = new Set((preview.missing_cells || []).map(([r, c]) => `${r}:${c}`));
  return (
    <div className="bb-grid-card bnf-lens-section" data-guide="census-lens-rows">
      <div className="bnf-lens-section-title">Exactly what {carrier} receives</div>
      {preview.total_rows === 0 ? (
        <div className="bnf-export-empty">No roster yet — this file would export empty.</div>
      ) : (
        <>
          <div className="bnf-export-preview-scroll">
            <table className="bnf-export-preview-table">
              <thead>
                <tr>
                  <th className="bnf-export-rownum">#</th>
                  {preview.headers.map((header, index) => (
                    <th key={index} title={preview.letters?.[index]}>
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, ri) => (
                  <tr key={ri}>
                    <td className="bnf-export-rownum">{ri + 1}</td>
                    {row.map((value, ci) => (
                      <td key={ci} className={missing.has(`${ri}:${ci}`) ? 'bnf-export-cell-missing' : undefined}>
                        {value || '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="bnf-export-meta">
            <span>{previewWords(preview)} — the same builder the download and the packet run.</span>
            {missing.size > 0 && (
              <span className="bnf-export-legend">
                <span className="bnf-export-legend-swatch" />
                required cell is blank ({missing.size})
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
