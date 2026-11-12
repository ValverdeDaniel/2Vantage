import { useState } from 'react';
import { useQuotedFiles } from '../../api/asQuoted';

/*
 * Whether the file on the Scanned data panel has a printed table to show "As in the file" (plan.md §8.16; E42;
 * slice 21): one proposal file in scope that a landed read gave a table. A file that prints several lines has one
 * table per line, picked by a chip. → {offered, documentId, line, choices, pick}.
 */
export default function useFileTables(dealId, scope, enabled) {
  const files = useQuotedFiles(dealId, { enabled });
  const [picked, setPicked] = useState('');
  const one = scope.ids.length === 1 ? scope.ids[0] : null;
  const tables = (files.data ?? []).filter((entry) => entry.document === one);
  const current = tables.find((entry) => entry.line === picked) ?? tables[0] ?? null;
  return {
    offered: Boolean(enabled && current),
    documentId: current?.document ?? null,
    line: current?.line ?? '',
    choices: tables.map((entry) => ({ key: entry.line, label: entry.line_label })),
    pick: setPicked,
  };
}
