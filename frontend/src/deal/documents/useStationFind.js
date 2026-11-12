import { useMemo, useState } from 'react';
import { carrierForms, findTerms } from '../../lib/findText';

/*
 * Find's words and where it stands among the matches (plan.md §8.16; E60–E64, D127; the old DocumentsTab's findQuery,
 * findPos and findNonce). The words become terms with the carriers' nicknames folded (OQ14). `cursor(hits, scope)`
 * says {total, index, current, key}: a new query, view or filter (`scope`) starts again at match 1; `step(cursor, ±1)`
 * moves round the matches and returns the new current one. `nonce` changes on every step, so the same match is shown
 * again when stepped back to. The words never leave the browser (Q.8).
 */
export default function useStationFind(carriers) {
  const forms = useMemo(() => carrierForms(carriers ?? []), [carriers]);
  const [query, setQuery] = useState('');
  const [only, setOnly] = useState(false);
  const [pos, setPos] = useState({ at: 0, key: '' });
  const [nonce, setNonce] = useState(0);
  const terms = useMemo(() => findTerms(query, forms), [query, forms]);
  const words = terms.map((term) => term.word).join(' ');

  function cursor(hits, scope) {
    const key = `${words}~${scope}`;
    const total = hits.length;
    const index = pos.key === key && total ? Math.min(pos.at, total - 1) : 0;
    return { total, index, current: total ? hits[index] : null, key };
  }

  function step(at, dir, hits) {
    if (!at.total) return null;
    const next = (at.index + dir + at.total) % at.total;
    setPos({ at: next, key: at.key });
    setNonce((n) => n + 1);
    return hits[next];
  }

  return { query, setQuery, only: only && terms.length > 0, rawOnly: only, setOnly, terms, words, nonce, cursor, step };
}
