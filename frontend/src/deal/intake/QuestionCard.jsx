import QuestionRow from './QuestionRow';

/*
 * One of the form's four cards (plan.md §4.5, §8.9; B1), the old `bb-panel bnf-intake-section`: its title, then its
 * questions in the form's order. `rowProps(row)` comes from useIntakeForm.
 */
export default function QuestionCard({ section, rowProps }) {
  return (
    <div className="bb-panel bnf-intake-section" data-section={section.key}>
      <div className="bb-panel-title">{section.label}</div>
      {section.rows.map((row) => (
        <QuestionRow key={row.key} {...rowProps(row)} />
      ))}
    </div>
  );
}
