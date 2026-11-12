import cx from '../../../ui/cx';
import { printedWhere } from './asQuotedModel';

/*
 * Above a scanned quote's printed table (plan.md §8.14, §8.16; E42, F42; slice 21): the chips that pick which printed
 * table to show (the Advisor's: one per scanned file; Documents': one per line when the file prints several), and
 * what the table is — where the file prints it, that the plans keep the file's column order and its rows their
 * printed order, that greyed rows fill no field, and how many of its plans have left the deal since.
 * `choices` = [{key, label, title?}], `current` a choice's key.
 */
export default function AsQuotedHead({ table, choices = [], current, onPick }) {
  const gone = table?.left_out ?? 0;
  return (
    <div className="gs-toolbar">
      {choices.length > 1 && (
        <div className="gs-filters" role="group" aria-label="Which printed table">
          {choices.map((choice) => (
            <button
              key={choice.key}
              type="button"
              className={cx('bnf-frl-chip', choice.key === current && 'is-on')}
              aria-pressed={choice.key === current}
              title={choice.title}
              onClick={() => onPick(choice.key)}
            >
              {choice.label}
            </button>
          ))}
        </div>
      )}
      {table && (
        <div className="bb-subtitle" data-as-quoted>
          As printed on {printedWhere(table)} of “{table.label}” ({table.line_label}): the plans in the file’s column
          order and the rows in printed order. Greyed rows fill no field, so they stay as the file prints them.
          {gone > 0 && ` ${gone} plan${gone === 1 ? '' : 's'} from this table ${gone === 1 ? 'is' : 'are'} no longer on the deal.`}
        </div>
      )}
    </div>
  );
}
