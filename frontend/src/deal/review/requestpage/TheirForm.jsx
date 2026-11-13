import { useEffect } from 'react';
import { usePreviewForm } from '../../../api/reviewForm';
import { useDebouncedValue } from '../../../lib/useDebouncedValue';
import PortalForm from '../../../portal/PortalForm';
import PortalShell from '../../../portal/PortalShell';
import InlineError from '../../../ui/InlineError';
import Loading from '../../../ui/Loading';

/*
 * Their form, in the middle of the request page (plan.md §8.8; L30; old 891f1b3 `RequestPage.jsx` the embedded portal,
 * `portalPreview.js`): the page the picked person would open, built by the portal's own builder from what is ticked
 * (a link's change waiting for Update link, or a new link's asks), never written then rolled back (P5). Only what is
 * asked shows; "N new · not sent" says what Update link adds; a change that cannot go shows the link as it stands, with
 * why. Read-only: nothing typed here is saved (edit mode is ours, L35). `body` is the preview's (null: nothing yet).
 */
export default function TheirForm({ dealId, body, who, frameRef = null }) {
  const key = useDebouncedValue(JSON.stringify(body || null), 350);
  const preview = usePreviewForm(dealId, JSON.parse(key));
  const fresh = (preview.data?.new_refs || []).join('|');
  // "New · not sent" on what Update link adds (old `bnf-ask-new`): a tag beside each new item in their form.
  useEffect(() => {
    const frame = frameRef?.current;
    if (!frame) return undefined;
    const tags = fresh
      ? fresh.split('|').flatMap((ref) => [...frame.querySelectorAll(`[data-ask-ref="${CSS.escape(ref)}"]`)])
      : [];
    const made = tags.map((anchor) => {
      const tag = document.createElement('span');
      tag.className = 'bnf-ask-new';
      tag.textContent = 'New · not sent';
      anchor.prepend(tag);
      return tag;
    });
    return () => made.forEach((tag) => tag.remove());
  }, [fresh, frameRef, preview.dataUpdatedAt]);
  return (
    <div className={`rr-preview${preview.isFetching ? ' rr-preview-stale' : ''}`} aria-label="Their form">
      <div className="rr-reqpage-colhead">
        <b>Their form</b>
        <span className="rr-edit-note">
          {who ? ` · as ${who} sees it` : ' · as they would see it'}
          {preview.data?.new_refs?.length > 0 && ` · ${preview.data.new_refs.length} new · not sent`}
        </span>
      </div>
      {preview.data?.why && <div className="rr-preview-why">{preview.data.why}</div>}
      {!body && <div className="rr-edit-note">Tick what to ask: their form shows here as they will see it.</div>}
      {body && preview.isPending && <Loading label="Building their form…" />}
      {body && preview.isError && <InlineError title="Their form" error={preview.error} onRetry={() => preview.refetch()} />}
      {body && preview.data && (
        <div className="rr-preview-frame" ref={frameRef}>
          <PortalShell agency={preview.data.page.agency} daysLeft={preview.data.page.days_left} preview className="bnf-portal-embed">
            <PortalForm token="" page={preview.data.page} readOnly onReload={() => preview.refetch()} onChallenge={() => {}} />
          </PortalShell>
        </div>
      )}
    </div>
  );
}
