import { Link } from 'react-router';
import { noCensusWords, readinessClass } from './requestModel';

const plural = (count, noun) => `${count} ${noun}${count === 1 ? '' : 's'}`;

/*
 * The census in one line (plan.md §8.12; K8; old CarriersTab.jsx at 891f1b3, same classes and words): employees,
 * dependents, readiness (green from 90 %, amber from 70 %, else rose), errors, and where to check it. With no census it
 * says where the band's count came from instead (K17).
 */
export default function CensusLine({ dealId, census, band }) {
  return (
    <div className="bnf-rfp-census-status bb-mb" data-guide="rfp-census-status">
      <b>Census</b>
      {census.has_roster ? (
        <>
          {' · '}
          {plural(census.employees, 'employee')}
          {' · '}
          {plural(census.dependents, 'dependent')}
          {' · '}
          <span className={readinessClass(census.readiness_pct)}>{census.readiness_pct}% ready</span>
          {census.errors > 0 && (
            <>
              {' · '}
              <span className="bb-rose">{plural(census.errors, 'error')}</span>
            </>
          )}
        </>
      ) : (
        <>
          {' · '}
          {noCensusWords(band)}
        </>
      )}
      {' — '}
      <Link className="bnf-override-link" to={`/deals/${dealId}/census`}>
        Check it on the Census tab ▸
      </Link>
    </div>
  );
}
