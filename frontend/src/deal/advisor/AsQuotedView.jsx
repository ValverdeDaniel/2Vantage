import { Suspense, lazy, useState } from 'react';
import Loading from '../../ui/Loading';

// The table is the Documents station's Grid, loaded only when this view opens, so the board never loads the station.
const AsQuotedBoard = lazy(() => import('../documents').then((module) => ({ default: module.AsQuotedBoard })));

const keyOf = (entry) => `${entry.document}:${entry.line}`;

/*
 * The Advisor's "As quoted" view (plan.md §8.14; F42; need 3; slice 21): one chip per scanned quote a read landed (a
 * file that prints several lines has one per line), and that quote as the carrier printed it — its plans in the
 * file's column order, its rows in printed order, the rows that fill no field greyed with their printed text. It
 * opens on the first table of the line the Advisor shows. `files` are `plans/as-quoted/`'s entries.
 */
export default function AsQuotedView({ deal, meta, files, line }) {
  const [picked, setPicked] = useState('');
  const current = files.find((entry) => keyOf(entry) === picked) ?? files.find((e) => e.line === line) ?? files[0];
  if (!current) return <Loading label="Loading the scanned quotes…" />;
  const lines = new Map();
  for (const entry of files) lines.set(entry.document, (lines.get(entry.document) ?? 0) + 1);
  const choices = files.map((entry) => ({
    key: keyOf(entry),
    label: lines.get(entry.document) > 1 ? `${entry.label} · ${entry.line_label}` : entry.label,
    title: `${entry.plans} plan${entry.plans === 1 ? '' : 's'} · ${entry.line_label}`,
  }));
  return (
    <Suspense fallback={<Loading label="Loading the quote as printed…" />}>
      <AsQuotedBoard
        deal={deal}
        meta={meta}
        documentId={current.document}
        line={current.line}
        choices={choices}
        current={keyOf(current)}
        onPick={setPicked}
      />
    </Suspense>
  );
}
