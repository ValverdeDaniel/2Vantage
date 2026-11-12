import { useQuery } from '@tanstack/react-query';
import { useCallback } from 'react';
import { useParams } from 'react-router';
import Loading from '../ui/Loading';
import { detailOf, getPage, statusOf } from './portalApi';
import PortalForm from './PortalForm';
import PortalGate from './PortalGate';
import PortalShell from './PortalShell';
import Unavailable from './Unavailable';
import usePortalStamp from './usePortalStamp';

const INVALID = "This link isn't valid. Please check you copied all of it, or ask your benefits contact for a new one.";

/*
 * `/portal/:token` (plan.md §8.1, §8.20; L76–L110 V2): the client's page, outside the app shell. It reads the page
 * (the open is counted by that read), shows the PIN screen on 428, "Link unavailable" with the agency's contact on
 * 404 and 410, and otherwise the form; its poll re-reads the page when what it asks changes (L103). The token never
 * leaves this route: no analytics, no referrer (the server says no-referrer and noindex).
 */
export default function PortalPage() {
  const { token } = useParams();
  const page = useQuery({
    queryKey: ['portal', token],
    queryFn: () => getPage(token),
    retry: false,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
  const { refetch } = page;
  const reload = useCallback(() => refetch(), [refetch]);
  const data = page.data;
  usePortalStamp(token, data?.form_stamp, reload, Boolean(data) && !page.isError);

  if (page.isPending) {
    return (
      <PortalShell>
        <Loading label="Loading..." />
      </PortalShell>
    );
  }
  if (page.isError && !data) {
    const code = statusOf(page.error);
    const body = page.error?.response?.data || {};
    if (code === 428) {
      return <PortalGate token={token} agency={body.agency} locked={Boolean(body.locked)} onVerified={reload} />;
    }
    return (
      <PortalShell agency={body.agency}>
        <Unavailable sentence={code === 410 ? detailOf(page.error) : INVALID} agency={body.agency} />
      </PortalShell>
    );
  }
  if (page.isError && statusOf(page.error) === 428) {
    const body = page.error.response.data || {};
    return <PortalGate token={token} agency={body.agency || data.agency} locked={Boolean(body.locked)} onVerified={reload} />;
  }
  if (page.isError && statusOf(page.error) === 410) {
    return (
      <PortalShell agency={data.agency}>
        <Unavailable sentence={detailOf(page.error)} agency={page.error.response.data?.agency || data.agency} />
      </PortalShell>
    );
  }
  return (
    <PortalShell agency={data.agency} daysLeft={data.days_left} staff={data.staff}>
      <PortalForm token={token} page={data} onReload={reload} onChallenge={reload} />
    </PortalShell>
  );
}
