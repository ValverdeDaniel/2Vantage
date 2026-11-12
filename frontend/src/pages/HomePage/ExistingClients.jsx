import { Link } from 'react-router';
import { useClients } from '../../api/deals';
import { useDebouncedValue } from '../../lib/useDebouncedValue';

/** "Already here? Example Co. — open": up to 5 existing clients whose name contains what was typed (plan.md §8.3). */
export default function ExistingClients({ name, onOpen }) {
  const typed = useDebouncedValue(name.trim(), 250);
  const matches = useClients({ q: typed }, { enabled: typed.length >= 2 });
  const rows = typed.length >= 2 ? (matches.data?.results || []).slice(0, 5) : [];
  return (
    <div aria-live="polite">
      {rows.length > 0 && (
        <div className="bnf-tiersource-note bb-mb">
          <strong>Already here?</strong>
          {rows.map((row) => (
            <div key={row.id}>
              {row.name} —{' '}
              <Link to={`/deals/${row.deal.id}`} onClick={onOpen} aria-label={`Open ${row.name}`}>
                open
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
