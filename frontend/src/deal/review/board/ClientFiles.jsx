import { useStartRead } from '../../../api/ai';
import { useMeta } from '../../../api/meta';
import { errorText } from '../../../lib/errors';
import { formatDate } from '../../../lib/format';
import { useToast } from '../../../ui/useToast';
import { claudeDoor } from '../../claude';
import { canRead, readWords } from './fileRows';

/*
 * The client's files on the To review lane's Documents card (plan.md §8.8; L9, L125, G101; slice 59), on the old
 * request page's file rows (891f1b3 `RequestCards.jsx` `FileRows`: `rr-rcard-file*`): each file by the slot it answered
 * and the day it came — never its name, often the people's (file names are PHI, plan §3.8; the Documents tab opens
 * it) — where its read stands, and "Read with Claude ▸" — the read of its kind's reader
 * (a renewal or a quote: the quote reader; a paper questionnaire: the questionnaire's; an invoice: intake's), with Work
 * with Claude opened to show it going and, when it is done, its review. Census and intake files a client uploads are
 * read by themselves (OQ89); the rest wait for this click. Shown only with Claude set up.
 */
export default function ClientFiles({ dealId, files, more, readOnly }) {
  const toast = useToast();
  const start = useStartRead(dealId);
  const { data: meta } = useMeta();
  const claude = Boolean(meta?.ai) && !readOnly;

  async function read(file) {
    try {
      await start.mutateAsync({ documentIds: [file.id], target: file.reader });
      toast.success('Claude is reading it. What it finds waits for your review in Work with Claude.');
      claudeDoor.open();
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <div className="rr-rcard-files">
      {files.map((file) => (
        <div key={file.id} className="rr-rcard-file">
          <div className="rr-rcard-file-h">
            <b>{file.label}</b>
            <span>Came {formatDate(file.at)}</span>
          </div>
          {readWords(file) && <div className="rr-rcard-file-state">{readWords(file)}</div>}
          {claude && canRead(file) && (
            <div className="rr-rcard-decide">
              <button
                type="button"
                className="rr-linklike"
                disabled={start.isPending}
                title="Read it with Claude: what it finds waits for your review, nothing changes until you use it"
                onClick={() => read(file)}
              >
                Read with Claude ▸
              </button>
            </div>
          )}
        </div>
      ))}
      {more > 0 && <div className="rr-rcard-file-state">+{more} more on the Documents tab</div>}
    </div>
  );
}
