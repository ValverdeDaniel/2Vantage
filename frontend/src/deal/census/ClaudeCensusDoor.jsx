import { useEffect, useRef } from 'react';
import Button from '../../ui/Button';
import { claudeDoor } from '../claude';
import { censusReader } from './claudeCensus';

/*
 * "Scan the census with Claude ▸" (plan.md §8.10, §8.17; C10, C11, D41; slice 51): the old empty roster's first door.
 * It opens Work with Claude on the census: a PDF roster dropped there is read person by person and waits as an import
 * on this tab; a spreadsheet's columns are mapped, the ones the offline mapper leaves proposed by Claude from their
 * shapes. On an empty roster the drawer opens by itself once (the old CensusTab's auto-open, never over a mapping
 * waiting for review). While the PHI-gate switch keeps the census reader off, the door shows greyed with the reason;
 * without Claude it is not there (D26).
 */
export default function ClaudeCensusDoor({ meta, autoOpen = false }) {
  const reader = censusReader(meta);
  const opened = useRef(false);
  useEffect(() => {
    if (!autoOpen || reader.state !== 'on' || opened.current) return;
    opened.current = true;
    claudeDoor.open('census');
  }, [autoOpen, reader.state]);
  if (!reader.state) return null;
  return (
    <Button
      variant="primary"
      size="sm"
      disabled={reader.state === 'off'}
      title={reader.why}
      onClick={() => claudeDoor.open('census')}
    >
      Scan the census with Claude ▸
    </Button>
  );
}
