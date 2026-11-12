import { useRef, useState } from 'react';
import { useStartImport } from '../../api/census';
import { useDocuments } from '../../api/documents';
import { errorText } from '../../lib/errors';
import Button from '../../ui/Button';
import Select from '../../ui/Select';
import { useToast } from '../../ui/useToast';

/*
 * The import door (plan.md §5.3.2, §8.10; C12): a census spreadsheet goes in through documents' one upload door (kind
 * Census), and its columns are mapped next; a census file already on the deal can be mapped as it is. Laid out in the
 * old empty roster's row of doors (`bnf-census-empty-actions`). Claude's scan of a census (PDF rosters included) is
 * slice 51's; adding people by hand and asking the client for the file come with the roster grid and the request tray.
 */
export default function ImportDoor({ dealId, meta, onStarted, label = 'Import a census file ▸', primary = true }) {
  const toast = useToast();
  const input = useRef(null);
  const [picked, setPicked] = useState('');
  const start = useStartImport(dealId);
  const documents = useDocuments(dealId);
  const censusFiles = (documents.data || []).filter((doc) => doc.kind === 'census' && doc.shape === 'sheet');
  const accept = (meta?.census?.import_accept || []).join(',');

  function begin(body) {
    start.mutate(body, {
      onSuccess: (imp) => onStarted(imp),
      onError: (error) => toast.error(errorText(error)),
    });
  }

  return (
    <div className="bnf-census-empty-actions">
      <input
        ref={input}
        type="file"
        accept={accept}
        hidden
        aria-label="Census file"
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = '';
          if (file) begin({ file });
        }}
      />
      <Button
        variant={primary ? 'primary' : 'secondary'}
        size="sm"
        busy={start.isPending}
        onClick={() => input.current?.click()}
      >
        {start.isPending ? 'Reading the file…' : label}
      </Button>
      {censusFiles.length > 0 && (
        <>
          <Select
            className="filter-select"
            aria-label="A census file on this deal"
            value={picked}
            placeholder="or a census file on this deal…"
            onChange={(event) => setPicked(event.target.value)}
            options={censusFiles.map((doc) => ({
              value: doc.id,
              label: doc.display_name,
            }))}
          />
          <Button size="sm" disabled={!picked || start.isPending} onClick={() => begin({ documentId: Number(picked) })}>
            Map this file ▸
          </Button>
        </>
      )}
    </div>
  );
}
