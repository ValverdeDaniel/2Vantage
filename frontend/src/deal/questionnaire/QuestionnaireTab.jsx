import { useSearchParams } from 'react-router';
import { useDealForms } from '../../api/questionnaire';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import FormChips from './FormChips';
import FormEditor from './FormEditor';

/*
 * The Questionnaire tab (plan.md §8.11; G1–G55, G133): the forms the deal uses — Florida Blue 51+ by the band at 51 or
 * more enrolled, Warner 51+ or the SIIA disclosure by a person's choice — one at a time, picked by chip and named in
 * `?form=` (G35); `?view=table` lays it out as a table (G38). Board, Request and Review are Review & requests' views
 * of the questionnaire (G34, slice 53). The sidebar shows the tab only while the deal has a form (G7).
 */
export default function QuestionnaireTab({ deal }) {
  const forms = useDealForms(deal.id);
  const [params, setParams] = useSearchParams();

  if (forms.isError) {
    return <InlineError title="Could not load the questionnaires." error={forms.error} onRetry={() => forms.refetch()} />;
  }
  if (forms.isPending) return <Loading label="Loading the questionnaires…" />;
  const list = forms.data.forms;
  if (!list.length) {
    return (
      <div className="card bnf-q-none">
        <p>
          This group’s size band doesn’t have an in-app carrier questionnaire yet — it stays a document request on the
          Marketing Checklist.
        </p>
      </div>
    );
  }
  const asked = params.get('form');
  const active = list.some((form) => form.key === asked) ? asked : list[0].key;
  const layout = params.get('view') === 'table' ? 'table' : 'form';
  const write = (changes) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)));
    setParams(next, { replace: true });
  };
  return (
    <div className="bnf-q-tab">
      <FormChips forms={list} active={active} onPick={(form) => write({ form })} />
      <FormEditor
        key={active}
        deal={deal}
        form={active}
        layout={layout}
        onLayout={(view) => write({ form: active, view: view === 'table' ? 'table' : '' })}
      />
    </div>
  );
}
