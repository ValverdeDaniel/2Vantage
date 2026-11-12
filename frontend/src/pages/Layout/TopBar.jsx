import { Link, useLocation } from 'react-router';
import { useAgency } from '../../api/deals';
import { useAuth } from '../../auth/useAuth';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import AdminMenu from './AdminMenu';

/**
 * The old top bar (A6, plan.md §8.1; Navbar.jsx at 891f1b3): the agency's name, Benefits, Commissions (a commission
 * tier other than none), Admin (admins), the username (Django's Change password page) and Logout. The old Calendar
 * link waits with the Radar (I88); the other old links are modules out of scope.
 */
export default function TopBar() {
  const { user, signOut } = useAuth();
  const agency = useAgency();
  const toast = useToast();
  const location = useLocation();

  async function onSignOut() {
    try {
      await signOut();
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <nav className="navbar" aria-label="Main">
      <Link to="/" className="navbar-brand">
        {agency.data?.name || '2Vantage'}
      </Link>
      <div className="navbar-user">
        <Link to="/">Benefits</Link>
        {user.commissions_access !== 'none' && <Link to="/commissions">Commissions</Link>}
        {user.is_admin && <AdminMenu key={`${location.pathname}${location.search}`} />}
        <a href="/accounts/password_change/" title="Change password">
          {user.username}
        </a>
        <button type="button" onClick={onSignOut} className="btn btn-danger">
          Logout
        </button>
      </div>
    </nav>
  );
}
