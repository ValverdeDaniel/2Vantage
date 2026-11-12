import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { prefetchRfp } from '../../api/rfp';

/**
 * The workspace's warm-up (K3, D-115): once the deal header has loaded and the browser is idle, the RFP payload is
 * fetched into its usual cache, so the tab's first click is instant (Daniel chose "warm in background"). A tab that
 * wants the same joins here; the RFP is the first.
 */
export default function useWarmTabs(dealId) {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (!dealId) return undefined;
    const warm = () => prefetchRfp(queryClient, dealId);
    if (window.requestIdleCallback) {
      const handle = window.requestIdleCallback(warm);
      return () => window.cancelIdleCallback(handle);
    }
    const handle = window.setTimeout(warm, 200);
    return () => window.clearTimeout(handle);
  }, [queryClient, dealId]);
}
