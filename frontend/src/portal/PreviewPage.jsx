import { useParams } from 'react-router';
import { usePreviewLink } from '../api/portalPreview';
import InlineError from '../ui/InlineError';
import Loading from '../ui/Loading';
import PortalForm from './PortalForm';
import PortalShell from './PortalShell';

/*
 * `/preview/links/:linkId` (plan.md §8.1; L78): View as client, for staff. The page a link opens, read-only under the
 * "Preview" banner: nothing typed is saved, no open is counted, and no PIN is asked (a person signed in sees it all
 * in the app anyway).
 */
export default function PreviewPage() {
  const { linkId } = useParams();
  const page = usePreviewLink(linkId);
  if (page.isPending) {
    return (
      <PortalShell preview>
        <Loading label="Loading..." />
      </PortalShell>
    );
  }
  if (page.isError) {
    return (
      <PortalShell preview>
        <InlineError title="Could not open this link's page." error={page.error} onRetry={() => page.refetch()} />
      </PortalShell>
    );
  }
  return (
    <PortalShell agency={page.data.agency} daysLeft={page.data.days_left} preview>
      <PortalForm token="" page={page.data} readOnly onReload={() => page.refetch()} onChallenge={() => {}} />
    </PortalShell>
  );
}
