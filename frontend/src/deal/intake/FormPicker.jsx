import { useChooseForm, useDealForms } from '../../api/questionnaire';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';

/*
 * The checklist row's form picker (B22; G2–G4, G9, G133), the old `bnf-q-formpick` (891f1b3 `MarketingChecklist.jsx`):
 * on the medical questionnaire "Fillable form:" — "Auto by group size — <the band's form>", each medical form, or
 * "No fillable form — upload only" — with "Chosen by you" once a person picked; on the stop-loss disclosure "Needed
 * for this group?" until a form is picked — "Not needed for this group", "Needed — <form>" or "Needed — upload only".
 * The choices and their words are /api/meta/'s (`questionnaires`); the deal's state is the questionnaire's
 * (`GET deals/{id}/questionnaires/`). A signed form can no longer be swapped; the band notice offers Keep or Switch.
 */
export default function FormPicker({ deal, meta, item }) {
  const toast = useToast();
  const forms = useDealForms(deal.id);
  const choose = useChooseForm(deal.id);
  const options = (meta?.questionnaires?.items || []).find((entry) => entry.key === item.key)?.options || [];
  const state = forms.data?.items?.[item.key];
  if (!options.length || !state) return null;
  const medical = item.key === 'medical_questionnaire';
  const auto = medical && state.choice === 'auto';
  const labelOf = (option) => {
    if (option.key !== 'auto') return option.label;
    const band = state.band_form ? options.find((o) => o.key === state.band_form)?.label : 'upload only';
    return `${option.label} — ${band}`;
  };
  const pick = (choice) =>
    choose.mutate(
      { item: item.key, choice },
      { onError: (error) => toast.error(errorText(error, { fallback: 'Could not change the form.' })) },
    );
  const notice = state.notice;
  return (
    <div className="bnf-q-formpick">
      <label>
        {medical || state.needed ? 'Fillable form:' : 'Needed for this group?'}{' '}
        <select
          className="bnf-q-formselect"
          value={state.choice}
          disabled={state.signed || choose.isPending}
          onChange={(event) => pick(event.target.value)}
        >
          {options.map((option) => (
            <option key={option.key} value={option.key}>
              {auto || option.key !== 'auto' ? labelOf(option) : option.label}
            </option>
          ))}
        </select>
      </label>
      {state.source === 'producer' && state.form && <span className="bb-badge bb-badge-muted">Chosen by you</span>}
      {state.source === 'band' && state.form && !auto && (
        <span className="bb-badge bb-badge-muted">Chosen by group size</span>
      )}
      {state.signed && <span className="bnf-marketing-detail">{meta.questionnaires.signed_lock}</span>}
      {notice && (
        <span className="bnf-marketing-detail">
          {notice.text} —{' '}
          <button type="button" className="bnf-override-link" onClick={() => pick(notice.keep)}>
            {notice.keep_label}
          </button>
          {' · '}
          <button type="button" className="bnf-override-link" onClick={() => pick(notice.switch)}>
            {notice.switch_label}
          </button>
        </span>
      )}
    </div>
  );
}
