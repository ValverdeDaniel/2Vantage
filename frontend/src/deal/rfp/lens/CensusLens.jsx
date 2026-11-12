import { useSearchParams } from 'react-router';
import { useRfpFormats } from '../../../api/rfp';
import ExportReadiness from './ExportReadiness';
import FormatLens from './FormatLens';
import LensChips from './LensChips';

const ROSTER = 'roster';

/*
 * The census format lens as the Census tab mounts it (plan.md §8.12; K79–K89; OQ63: both the Export readiness cards
 * and the chips; old CensusFormatLens.jsx and ExportReadiness.jsx at 891f1b3): the readiness cards, then the chips —
 * "Our census" shows the tab's own roster (`children`), a carrier format shows that format's lens. The format picked
 * is in the address (`?lens=census-uhc`), which is where the RFP packet's "Check ▸" lands. The old app drew these on
 * the census Board view; until 2Vantage's census views arrive (slices 53, 57) the roster shows alone unless a format
 * is asked for, so the Roster view keeps its old look and the format list is fetched only then.
 */
export default function CensusLens({ dealId, children }) {
  const [params, setParams] = useSearchParams();
  const wanted = params.get('lens') || '';
  const list = useRfpFormats(dealId, Boolean(wanted));
  const formats = list.data?.formats || [];
  const active = formats.find((format) => format.key === wanted) || null;
  // "Our census" keeps the chips on screen (`?lens=roster`): the roster under them, as the old Board view drew it.
  const pick = (key) =>
    setParams(
      (now) => {
        const next = new URLSearchParams(now);
        next.set('lens', key || ROSTER);
        return next;
      },
      { replace: true },
    );
  if (!wanted || !formats.length) return children;
  return (
    <>
      <ExportReadiness dealId={dealId} formats={formats} active={active?.key || ''} onPick={pick} />
      <LensChips formats={formats} active={active?.key || ''} onPick={pick} />
      {active ? <FormatLens key={active.key} dealId={dealId} format={active} /> : children}
    </>
  );
}
