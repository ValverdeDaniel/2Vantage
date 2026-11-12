import { createElement, useState } from 'react';
import { useNavigate } from 'react-router';
import { downloadRfpFile, fetchRfpCheck } from '../../api/rfp';
import CheckModal from '../../exportcheck/CheckModal';
import useDownloadCheck from '../../exportcheck/useDownloadCheck';
import { useToast } from '../../ui/useToast';

/*
 * One door for every RFP download (plan.md §7.11; K50, K51, K69, K70, K113): a census file, a form, the cover, a
 * questionnaire, an attachment, the packet or a draft's `.eml`. "Before you download: …" opens first with the check of
 * exactly that key (the shared modal, src/exportcheck/); the download sends its `ack`, and a check that changed since
 * comes back as the fresh report (409). The server builds and names the file; the button says "Building…" while it
 * does; a refusal (no census yet, a file that cannot be built) shows in the modal, in words. Fix ▸ goes where the problem is.
 *   const files = useRfpDownload(dealId); files.download(key, label); render files.modal
 */
export default function useRfpDownload(dealId) {
  const toast = useToast();
  const navigate = useNavigate();
  const [current, setCurrent] = useState('');
  const check = useDownloadCheck({ onDone: (name) => toast.success(`${name || 'File'} downloaded`) });

  const download = (key, label) => {
    setCurrent(key);
    check.run({
      label,
      check: () => fetchRfpCheck(dealId, key),
      download: (ack) => downloadRfpFile(dealId, key, ack),
    });
  };

  const fix = (target) => {
    check.close();
    const params = new URLSearchParams();
    for (const name of ['lens', 'form', 'view']) if (target[name]) params.set(name, target[name]);
    const query = params.toString();
    navigate(`/deals/${dealId}/${target.tab}${query ? `?${query}` : ''}`);
  };

  const modal = check.state
    ? createElement(CheckModal, { state: check.state, onClose: check.close, onDownload: check.download, onFix: fix })
    : null;
  const working = check.state && (check.state.loading || check.state.busy);
  return { busy: working ? current : '', download, modal };
}
