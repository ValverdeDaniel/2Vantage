import { LOST, stageLadder } from '../../api/meta';
import cx from '../../ui/cx';
import VisuallyHidden from '../../ui/VisuallyHidden';
import styles from './StageStepper.module.css';

/** Intake ── Quoting ── Proposal ── Sold, the current stage highlighted (and named for screen readers). */
export default function StageStepper({ stage, meta }) {
  const ladder = stageLadder(meta);
  const currentIndex = ladder.findIndex((step) => step.key === stage);
  return (
    <ol className={cx(styles.stepper, stage === LOST && styles.lost)} aria-label="Deal stage">
      {ladder.map((step, index) => {
        let state = 'todo';
        if (currentIndex >= 0 && index < currentIndex) state = 'done';
        if (index === currentIndex) state = 'current';
        return (
          <li key={step.key} className={cx(styles.step, styles[state])} aria-current={state === 'current' ? 'step' : undefined}>
            <span className={styles.dot} aria-hidden="true">
              {state === 'done' ? '✓' : index + 1}
            </span>
            <span className={styles.label}>{step.label}</span>
            {state === 'current' && <VisuallyHidden> (current stage)</VisuallyHidden>}
            {state === 'done' && <VisuallyHidden> (done)</VisuallyHidden>}
          </li>
        );
      })}
    </ol>
  );
}
