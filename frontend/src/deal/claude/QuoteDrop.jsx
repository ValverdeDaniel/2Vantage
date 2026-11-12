import { useState } from 'react';
import { useMeta } from '../../api/meta';
import ClaudeDrawer, { ReadingPicker } from './ClaudeDrawer';
import DrawerBody from './DrawerBody';
import { tabKinds } from './drawerWords';
import useAttach from './useAttach';

/*
 * Work with Claude before the deal exists (plan.md §8.3; A14, D43; the old NewCase's ScanDrawer + ScanChat with
 * `resolveCaseId`): the quote-first door's drawer. Files dropped or attached here make the deal first (`ensureDeal`),
 * are filed as carrier quotes (or what the "Reading" picker says) and read at once; `onSent(dealId)` then opens the
 * deal (the Advisor, with the drawer open on the read).
 */
export default function QuoteDrop({ ensureDeal, onSent, onClose }) {
  const { data: meta } = useMeta();
  const kinds = tabKinds(meta, 'advisor');
  const [kind, setKind] = useState('');
  const shown = kinds.includes(kind) ? kind : kinds[0] || '';
  const attach = useAttach({ dealId: null, ensureDeal, kind: shown, meta, model: '', onSent });
  if (!meta?.ai || !shown) return null;
  return (
    <ClaudeDrawer
      headerExtra={<ReadingPicker kinds={kinds} kind={shown} meta={meta} onKind={setKind} disabled={attach.busy} />}
      onClose={onClose}
    >
      <DrawerBody dealId={null} meta={meta} state={null} kind={shown} kinds={kinds} files={[]} attach={attach} />
    </ClaudeDrawer>
  );
}
