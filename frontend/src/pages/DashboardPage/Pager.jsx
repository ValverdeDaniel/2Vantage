import Button from '../../ui/Button';
import styles from './Pager.module.css';

/** ‹ Prev   Page 1 of 3   Next › — hidden when everything fits on one page. */
export default function Pager({ page, count, pageSize = 25, onPage }) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (pages <= 1) return null;
  return (
    <nav aria-label="Pages" className={styles.pager}>
      <Button size="sm" variant="ghost" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        ‹ Prev
      </Button>
      <span className={styles.position}>
        Page {Math.min(page, pages)} of {pages}
      </span>
      <Button size="sm" variant="ghost" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Next ›
      </Button>
    </nav>
  );
}
