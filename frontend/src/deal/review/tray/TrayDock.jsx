import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { useMeta } from '../../../api/meta';
import { useTray, useTrayRemove } from '../../../api/reviewTray';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import TrayBar from './TrayBar';
import TraySnippet from './TraySnippet';
import { destinationOf } from './trayModel';

/*
 * The deal's request tray, on every tab (plan.md §8.8; L49, L50; old 891f1b3 `ReviewTrayDock.jsx`): the bar shows while
 * anything waits and names where it goes; a click opens the snippet — what is queued by section, × each, and "Open the
 * request ▸". `?tray=open` opens the snippet too. Neither shows on the request page itself, which is the full version of
 * both. Mounted once by the deal shell; one tray read, shared with every "＋ Ask" (L54).
 */
export default function TrayDock({ deal, tab }) {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const sections = useMeta().data?.review?.tray_sections || [];
  const tray = useTray(deal.id);
  const remove = useTrayRemove(deal.id);
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const byParam = params.get('tray') === 'open';
  const onPage = tab === 'review' && params.get('view') === 'request';
  const data = tray.data;
  if (!data || onPage) return null;
  const items = data.items || [];
  const snippet = open || byParam;
  if (!items.length && !snippet) return null;

  const close = () => {
    setOpen(false);
    if (byParam) {
      const next = new URLSearchParams(params);
      next.delete('tray');
      setParams(next, { replace: true });
    }
  };
  const destination = destinationOf(items);
  return (
    <>
      {!snippet && (
        <TrayBar
          count={items.length}
          destination={destination}
          nowhere={(data.needs_new || []).length}
          onOpen={() => setOpen(true)}
        />
      )}
      {snippet && (
        <TraySnippet
          items={items}
          sections={sections}
          destination={destination}
          busy={remove.isPending}
          onRemove={(item) => remove.mutateAsync([item.id]).catch((error) => toast.error(errorText(error)))}
          onClose={close}
          onOpenRequest={() => {
            setOpen(false);
            navigate(`/deals/${deal.id}/review?view=request`);
          }}
        />
      )}
    </>
  );
}
