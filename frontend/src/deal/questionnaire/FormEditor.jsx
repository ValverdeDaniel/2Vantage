import { useRef, useState } from 'react';
import { useQuestionnaire, useSpec } from '../../api/questionnaire';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import BandNotice from './BandNotice';
import FileActions from './FileActions';
import FormCheck from './FormCheck';
import PaperForm from './PaperForm';
import ReopenDialog from './ReopenDialog';
import SignatureCard from './SignatureCard';
import TableLayout from './TableLayout';
import Toolbar from './Toolbar';
import useAnswerDraft from './useAnswerDraft';
import useFormKeys from './useFormKeys';

/*
 * One form on the tab (G36–G44, G49–G56, G67, G133): the band notice, the toolbar with its file doors, the PDF pane
 * of "Check the form ▸", the "Signed by …" lock with Reopen, the paper or table layout and the signatures. Mounted per
 * form (`key`), so switching forms sends what waits first.
 */
export default function FormEditor({ deal, form, layout, onLayout }) {
  const spec = useSpec(form);
  const query = useQuestionnaire(deal.id, form);
  const draft = useAnswerDraft(deal, form, spec.data);
  const paperRef = useRef(null);
  const [reopening, setReopening] = useState(false);
  const [checking, setChecking] = useState(false);
  const data = query.data;
  const locked = Boolean(data?.locked);
  const onKeyDown = useFormKeys({ paperRef, spec: spec.data, data, draft: draft.draft, flush: draft.flush, locked });

  if (spec.isError || query.isError) {
    const failed = spec.isError ? spec : query;
    return <InlineError title="Could not load the questionnaire." error={failed.error} onRetry={() => failed.refetch()} />;
  }
  if (!spec.data || !data) return <Loading label="Loading the questionnaire…" />;

  const Layout = layout === 'table' ? TableLayout : PaperForm;
  return (
    <>
      <BandNotice deal={deal} item={data.item.item} notice={data.item.notice} />
      <Toolbar spec={spec.data} progress={data.progress} saving={draft.saving} layout={layout} onLayout={onLayout}>
        <FileActions
          deal={deal}
          form={form}
          spec={spec.data}
          locked={locked}
          checking={checking}
          onToggleCheck={() => setChecking((open) => !open)}
        />
      </Toolbar>
      {checking && <FormCheck dealId={deal.id} form={form} onClose={() => setChecking(false)} />}
      {data.version_mismatch && (
        <div className="bnf-review-note">
          This form was started on version {data.form_version}; the carrier’s form is now {data.version}.
        </div>
      )}
      {locked && (
        <div className="bnf-q-locked">
          Signed by {data.officer.name} — the form is now read-only. The signed PDF is still downloadable above.
          {' '}
          <button type="button" className="bnf-override-link" onClick={() => setReopening(true)}>
            Reopen the form ▸
          </button>
        </div>
      )}
      <div
        className={`bnf-q-paper ${layout === 'table' ? 'bnf-q-paper-plain' : ''}`}
        ref={paperRef}
        onKeyDown={onKeyDown}
      >
        <Layout
          spec={spec.data}
          data={data}
          draft={draft.draft}
          onChange={draft.change}
          onAddRow={draft.onAddRow}
          onRemoveRow={draft.onRemoveRow}
          disabled={locked}
        />
      </div>
      <SignatureCard deal={deal} spec={spec.data} data={data} flush={draft.flush} />
      <ReopenDialog deal={deal} form={form} open={reopening} onClose={() => setReopening(false)} />
    </>
  );
}
