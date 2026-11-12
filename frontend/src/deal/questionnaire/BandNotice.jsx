import { useChooseForm } from '../../api/questionnaire';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';

/*
 * The band notice (G133): the first answer froze the group size's form into the checklist choice, and the group size
 * now says otherwise. Nothing swaps silently: Keep makes the form a person's choice, Switch follows the group size
 * (refused on a signed form). Shown on the tab and on the checklist row.
 */
export default function BandNotice({ deal, item, notice }) {
  const toast = useToast();
  const choose = useChooseForm(deal.id);
  if (!notice) return null;
  const pick = (choice) =>
    choose.mutate(
      { item, choice },
      { onError: (error) => toast.error(errorText(error, { fallback: 'Could not change the form.' })) },
    );
  return (
    <div className="bnf-review-note" role="status">
      {notice.text} —{' '}
      <button type="button" className="bnf-override-link" disabled={choose.isPending} onClick={() => pick(notice.keep)}>
        {notice.keep_label}
      </button>
      {' · '}
      <button type="button" className="bnf-override-link" disabled={choose.isPending} onClick={() => pick(notice.switch)}>
        {notice.switch_label}
      </button>
    </div>
  );
}
