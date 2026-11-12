import { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router';
import { useDeal } from '../../api/deals';
import { useDocuments } from '../../api/documents';
import { labelOf, useMeta } from '../../api/meta';
import cx from '../../ui/cx';
import { HotkeyLegend } from '../../valuereview/HotkeyLegend';
import { dealPresence } from '../../viewer/docWindowLink';
import DocumentViewer from '../../viewer/DocumentViewer';
import { inUploadOrder } from './stationFiles';
import useWindowLink from './useWindowLink';

/*
 * A deal's file in a window of its own (plan.md §8.16, §8.1 route `/deals/:dealId/documents/:docId/window`; E69–E71,
 * D128, OQ99; the old DocumentWindow.jsx, D-125), opened from the Documents tab's ⧉ New window so the file can sit on
 * one screen and the scanned data on another. It says plainly which client it is for: the name, large, the deal's
 * year and the file, and whether it is linked. It shows what the tab sends — the file, and the value F opened — through
 * the same DocumentViewer, and sends back its page and the review keys pressed here. Its row of files picks one by
 * hand: it asks the tab (`open`), which moves its viewer, never its grid. When the tab leaves this client, the window
 * covers itself: "You're no longer working on <client>", until the tab comes back. It writes nothing itself.
 */
const STATUS = {
  linked: { text: 'Linked to the Documents tab in your other window', cls: 'dw-status-linked' },
  waiting: { text: 'Connecting to the Documents tab…', cls: 'dw-status-waiting' },
  left: { text: 'No longer linked', cls: 'dw-status-left' },
  gone: { text: 'The window this opened from is closed', cls: 'dw-status-left' },
};

function LeftCover({ status, client, elsewhere }) {
  return (
    <div className="dw-left" role="alertdialog" aria-labelledby="dw-left-title">
      <div className="dw-left-card">
        <div id="dw-left-title" className="dw-left-title">
          You’re no longer working on {client || 'this client'}
        </div>
        <div className="dw-left-text">
          {status === 'gone'
            ? 'The window this file was opened from is closed. Please close this window.'
            : elsewhere
              ? `Your other window moved on to ${elsewhere}. Please close this window.`
              : 'Your other window has left this client. Please close this window.'}
        </div>
        <button type="button" className="btn btn-primary" onClick={() => window.close()}>
          Close this window
        </button>
        {status === 'left' && (
          <div className="dw-left-sub">
            Go back to {client || 'this client'} in your other window and this one picks up again.
          </div>
        )}
      </div>
    </div>
  );
}

export default function DocumentWindowPage() {
  const { dealId, docId } = useParams();
  const [params] = useSearchParams();
  const validId = /^\d+$/.test(dealId || '');
  const header = useDeal(validId ? dealId : null);
  const documents = useDocuments(validId ? dealId : null);
  const meta = useMeta().data;
  const deal = dealPresence(header.data);
  const link = useWindowLink(params.get('link') || '', deal?.key || '');
  // A file picked here, until the tab's next `show` answers (with it, or with what F opened since).
  const [picked, setPicked] = useState({ id: null, under: null });
  const shown = link.shown;
  const files = inUploadOrder(documents.data);
  const byId = (id) => files.find((file) => file.id === Number(id)) || null;
  const pickedDoc = picked.id != null && picked.under === shown ? byId(picked.id) : null;
  const sentDoc = pickedDoc ? null : byId(shown?.docId);
  const doc = pickedDoc || sentDoc || byId(docId);
  const find = sentDoc ? shown.find || {} : {};
  const what = sentDoc ? shown.what || '' : '';
  const inScope = new Set(shown?.scope || []);
  const client = deal?.name || '';
  const fileName = doc ? doc.display_name || doc.original_name : '';

  useEffect(() => {
    document.title = client ? `${client}${fileName ? ` · ${fileName}` : ''} — 2Vantage` : 'Document — 2Vantage';
  }, [client, fileName]);

  if (!validId || header.isError || documents.isError) {
    return (
      <div className="dw-page">
        <div className="dw-empty">
          This deal could not be opened here. Close this window and open the file again from the Documents tab.
        </div>
      </div>
    );
  }
  const pick = (id) => {
    if (id === doc?.id) return;
    setPicked({ id, under: shown });
    if (link.status === 'linked') link.post({ type: 'open', docId: id });
  };
  const status = STATUS[link.status];
  return (
    <div className="dw-page" data-window-status={link.status}>
      <header className="dw-head">
        <div className="dw-client">
          <span className="dw-client-label">Client</span>
          <span className="dw-client-name">{client || '…'}</span>
        </div>
        <div className="dw-sub">
          {deal?.year ? `${deal.year} deal` : 'Deal'}
          {fileName ? (
            <>
              {' '}
              · <span className="dw-file">📄 {fileName}</span>
            </>
          ) : null}
        </div>
        {what && <div className="dw-what">Showing {what}</div>}
        {files.length > 1 && (
          <div className="dw-files" role="tablist" aria-label="The deal's files">
            {files.map((file) => (
              <button
                key={file.id}
                type="button"
                role="tab"
                aria-selected={file.id === doc?.id}
                data-dw-file={file.id}
                className={cx(
                  'dw-file-btn',
                  file.id === doc?.id && 'is-on',
                  inScope.has(file.id) && file.id !== doc?.id && 'is-inscope',
                )}
                title={
                  inScope.has(file.id)
                    ? 'The scanned data in your other window is from this file'
                    : 'Show this file here'
                }
                onClick={() => pick(file.id)}
              >
                📄 {file.display_name || file.original_name}
                {meta && <span className="dw-file-bucket">{labelOf(meta.document_buckets, file.bucket)}</span>}
              </button>
            ))}
          </div>
        )}
        <div className="dw-head-row">
          <span className={`dw-status ${status.cls}`} role="status">
            ● {status.text}
          </span>
          <span className="dw-keys">
            <span className="dw-keys-note">These keys work here too:</span>
            <HotkeyLegend relay />
          </span>
        </div>
      </header>
      <main className="dw-body">
        {doc ? (
          <DocumentViewer
            document={doc}
            find={find}
            jumpKey={sentDoc ? shown.jumpKey || 0 : 0}
            onPageChange={(page) => link.post({ type: 'page', page, docId: doc.id })}
          />
        ) : (
          <div className="dw-empty">
            Pick a file on the Documents tab in your other window, or select a value there and press F: it shows here.
          </div>
        )}
      </main>
      {(link.status === 'left' || link.status === 'gone') && (
        <LeftCover status={link.status} client={client} elsewhere={link.elsewhere} />
      )}
    </div>
  );
}
