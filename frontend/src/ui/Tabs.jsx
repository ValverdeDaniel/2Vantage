import { NavLink } from 'react-router';
import cx from './cx';
import styles from './Tabs.module.css';

/**
 * Tabs as navigation links: each tab is a route, so Back and links work. The current one gets aria-current="page"
 * and a bar beside it (not colour alone).
 *   items: [{to, label, badge?}] · label: the nav's accessible name · orientation: 'horizontal' | 'vertical'
 */
export default function Tabs({ items, label, orientation = 'horizontal', className }) {
  return (
    <nav aria-label={label} className={cx(styles.tabs, styles[orientation], className)}>
      <ul className={styles.list}>
        {items.map((item) => (
          <li key={item.to}>
            <NavLink to={item.to} className={({ isActive }) => cx(styles.tab, isActive && styles.active)}>
              <span>{item.label}</span>
              {item.badge}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
