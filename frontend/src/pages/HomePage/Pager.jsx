/** ‹ Prev   Page 1 of 3   Next › on the old census pager (`bnf-census-pager`); hidden when everything fits. */
export default function Pager({ words, onPage }) {
  if (!words) return null;
  const { page, pages } = words;
  return (
    <nav aria-label="Pages" className="bnf-census-pager">
      <button type="button" className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        ‹ Prev
      </button>
      <span className="bnf-census-pager-label">
        Page {page} of {pages}
      </span>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={page >= pages}
        onClick={() => onPage(page + 1)}
      >
        Next ›
      </button>
    </nav>
  );
}
