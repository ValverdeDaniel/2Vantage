import styles from './VisuallyHidden.module.css';

/** Text for screen readers only. */
export default function VisuallyHidden({ children, as: Tag = 'span', ...rest }) {
  return (
    <Tag className={styles.hidden} {...rest}>
      {children}
    </Tag>
  );
}
