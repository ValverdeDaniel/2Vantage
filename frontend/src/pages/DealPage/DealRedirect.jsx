import { Navigate, useParams, useSearchParams } from 'react-router';
import { tabFor } from './nav';
import { BUILT_TABS } from './tabs';

/**
 * /deals/:dealId opens the deal's default tab (the Advisor until slice 62). A link that names its tab in the query
 * (`?tab=documents`, the old workspace's way, A26) opens that tab in the path, keeping the rest of its query.
 */
export default function DealRedirect() {
  const { dealId } = useParams();
  const [params] = useSearchParams();
  const rest = new URLSearchParams(params);
  rest.delete('tab');
  const query = rest.toString();
  const tab = tabFor(params.get('tab'), BUILT_TABS);
  return <Navigate to={`/deals/${dealId}/${tab}${query ? `?${query}` : ''}`} replace />;
}
