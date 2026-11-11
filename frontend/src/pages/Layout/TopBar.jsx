import { Link, useLocation } from 'react-router';
import { useAuth } from '../../auth/useAuth';
import { errorText } from '../../lib/errors';
import cx from '../../ui/cx';
import Menu from '../../ui/Menu';
import { useToast } from '../../ui/useToast';
import styles from './TopBar.module.css';

/** 2Vantage · Clients · (Admin) · user menu (plan.md §8.1). Admin and Change password are Django's own pages. */
export default function TopBar() {
  const { user, signOut } = useAuth();
  const toast = useToast();
  const { pathname } = useLocation();
  const inClients = pathname === '/' || pathname.startsWith('/deals/');

  async function onSignOut() {
    try {
      await signOut();
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <header className={styles.bar}>
      <Link to="/" className={styles.brand}>
        2Vantage
      </Link>
      <nav aria-label="Main" className={styles.nav}>
        <Link
          to="/"
          className={cx(styles.link, inClients && styles.current)}
          aria-current={inClients ? 'page' : undefined}
        >
          Clients
        </Link>
      </nav>
      <div className={styles.end}>
        {user.is_admin && (
          <a href="/admin/" className={styles.link}>
            Admin
          </a>
        )}
        <Menu
          label={user.first_name || user.full_name || user.username}
          ariaLabel={`Account menu for ${user.full_name || user.username}`}
          align="end"
          buttonClassName={styles.userButton}
          items={[
            { key: 'password', label: 'Change password', href: '/accounts/password_change/' },
            { key: 'signout', label: 'Sign out', onSelect: onSignOut },
          ]}
        />
      </div>
    </header>
  );
}
