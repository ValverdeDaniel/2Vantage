import { useQuery } from '@tanstack/react-query';
import { getMoved } from './portalApi';
import PortalShell from './PortalShell';
import Unavailable from './Unavailable';

/*
 * `/b/:token` (plan.md §8.1; L136, Ch. 24): an old Vantage client link after the move. It says the link has moved and
 * how to reach the agency for a new one. The old token is never sent anywhere: the page reads only the agency's
 * contact, which takes no token.
 */
export default function MovedPage() {
  const moved = useQuery({ queryKey: ['portal', 'moved'], queryFn: getMoved, staleTime: Infinity, retry: false });
  const agency = moved.data?.agency;
  return (
    <PortalShell agency={agency}>
      <Unavailable
        title="This link has moved"
        sentence="We have moved to a new system, so this link no longer opens. Please ask your benefits contact for a new link."
        agency={agency}
      />
    </PortalShell>
  );
}
