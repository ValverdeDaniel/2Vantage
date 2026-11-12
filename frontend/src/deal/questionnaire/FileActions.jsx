import { useState } from 'react';
import { useNavigate } from 'react-router';
import { downloadBlank, downloadFilled, fetchCheck } from '../../api/questionnaire';
import { useToast } from '../../ui/useToast';
import CheckModal from '../../exportcheck/CheckModal';
import useDownloadCheck from '../../exportcheck/useDownloadCheck';
import DownloadMenu from './DownloadMenu';

const FILLED = 'The form with every answer in place, marked DRAFT until it is signed; checked before it downloads.';
const FILED = 'The signed copy, as filed in Documents; checked before it downloads.';
const BLANK = 'The carrier’s empty form, nothing filled in, to print or fill by hand.';

/*
 * The toolbar's file doors (G56, G61, G65–G67): "Check the form ▸" opens the PDF pane beside the problems, and the ⬇
 * menu offers the filled form — checked first, then downloaded with the check's `ack` — and the carrier's blank. Once
 * the officer has signed, "Download PDF" is the copy filed in Documents (G135). The server names every file (G62).
 */
export default function FileActions({ deal, form, spec, locked, checking, onToggleCheck }) {
  const toast = useToast();
  const navigate = useNavigate();
  const [fetching, setFetching] = useState(false);
  const label = spec.title || 'Questionnaire';
  const check = useDownloadCheck({ onDone: () => toast.success(`${label} downloaded`) });

  const blank = async () => {
    setFetching(true);
    try {
      await downloadBlank(deal.id, form);
    } catch {
      toast.error('No blank carrier form is available');
    } finally {
      setFetching(false);
    }
  };
  const filled = () =>
    check.run({
      label,
      check: () => fetchCheck(deal.id, form),
      download: (ack) => downloadFilled(deal.id, form, ack),
    });
  const items = [{ key: 'pdf', label: 'Download PDF', detail: locked ? FILED : FILLED, run: filled }];
  if (spec.has_blank_pdf) items.push({ key: 'blank', label: 'Blank carrier PDF', detail: BLANK, run: blank });

  const fix = (target) => {
    check.close();
    const params = new URLSearchParams({ form: target.form || form });
    if (target.view) params.set('view', target.view);
    navigate(`/deals/${deal.id}/${target.tab}?${params}`);
  };
  return (
    <>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        title={checking ? 'Hide the filled form' : 'The filled PDF as it will download, beside what is wrong with it'}
        onClick={onToggleCheck}
      >
        {checking ? 'Hide the form' : 'Check the form ▸'}
      </button>
      <DownloadMenu items={items} busy={fetching || Boolean(check.state?.busy)} />
      {check.state && <CheckModal state={check.state} onClose={check.close} onDownload={check.download} onFix={fix} />}
    </>
  );
}
