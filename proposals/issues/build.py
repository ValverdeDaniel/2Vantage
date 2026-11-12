"""The `issue` job (plan.md §7.12 "Issuing" step 2; J102, J103, J.6.4; Q.7: xlsx ≤3 s, PDF ≤6 s, pptx ≤8 s).
Registered with ai in ProposalsConfig.ready(); the worker runs it in the system lane, outside every lock.

It reads the deal as it stands, asks the gate again (a pick taken off since the click fails the version with that
sentence rather than issuing a proposal without our recommendation), then builds the three files from the downloads'
own builders, one layout pass for the PDF and the PowerPoint (`story.build.deck`, as the draft downloads use it):
- no Draft mark anywhere, "Version n" in the deck's footer (J102; OQ35), the spreadsheet's page headers bare;
- the J104 names without -DRAFT: `<Client> - <year> Benefits Proposal.pdf / .pptx / .xlsx`.
`finish.store` then keeps them; any failure marks the version failed with a sentence (`finish.fail`) and ends the job
failed, never with an exception's text (rule 10). Stop does the same; a worker shutting down puts it back in the queue.
"""

from ai.progress import Gone, JobFailed, Paused, Stopped

from ..models import ProposalIssue
from ..paint import pdf, pptx
from ..story import build as deck_build
from ..workbook import build as workbook_build
from ..workbook import facts as workbook_facts
from ..workbook import write
from . import finish, gate
from .catalog import EXTENSIONS

FAILED = 'The files could not be built. Retry; if it fails again, tell an admin.'
STOPPED = 'Stopped before the files were stored. Retry to build them.'
GONE = 'This stopped answering, so it was ended before the files were stored. Retry to build them.'
AREAS = ['proposal', 'documents', 'header', 'advisor']  # what a browser refetches once it lands


def files(deal, version, progress=None):
    """{key: (file name, bytes)}: version `version` of `deal`'s PDF, PowerPoint and workbook, as issued."""
    step = progress.step if progress else (lambda text, pct=None: None)
    step('Laying out the slides', 10)
    found = deck_build.deck(deal, version=version)
    step('Drawing the PDF', 30)
    pdf_bytes = pdf.draw(found['pages'], found['title'], found['sources'])
    step('Drawing the PowerPoint', 50)
    pptx_bytes = pptx.draw(found['pages'], found['title'], found['sources'])
    step('Writing the spreadsheet', 75)
    xlsx_bytes = write.to_bytes(workbook_build.from_facts(workbook_facts.read_deal(deal), draft=''))
    built = {'pdf': pdf_bytes, 'pptx': pptx_bytes, 'xlsx': xlsx_bytes}
    return {
        key: (workbook_build.filename(deal, draft=False, extension=EXTENSIONS[key]), data)
        for key, data in built.items()
    }


def _built(row, progress):
    progress.step(f'Reading proposal v{row.version}', 5)
    sentences = gate.blockers(row.deal)
    if sentences:
        raise JobFailed(' '.join(sentences))
    try:
        return files(row.deal, row.version, progress)
    except workbook_build.NothingToPresent as refusal:
        raise JobFailed(str(refusal)) from refusal


def run(job, progress):
    issue_id = int((job.params or {})['issue'])
    row = ProposalIssue.objects.select_related('deal__client', 'deal__owner').get(pk=issue_id)
    result = {'issue': row.id, 'version': row.version, 'landed': {'areas': AREAS, 'plan_ids': []}}
    if row.state != ProposalIssue.BUILDING:
        return {**result, 'state': row.state}
    try:
        built = _built(row, progress)
        progress.step('Storing the files', 95)
        row, written = finish.store(job, row.id, built)
    except Paused:
        raise  # back to the queue, still building
    except Stopped:
        finish.fail(job, issue_id, STOPPED)
        raise
    except Gone:
        finish.fail(job, issue_id, GONE)
        raise
    except JobFailed as exc:
        finish.fail(job, issue_id, exc.sentence)
        raise
    except Exception:
        finish.fail(job, issue_id, FAILED)
        raise
    progress.activity_id = written.id if written else None
    documents = {key: getattr(row, f'{key}_id') for key in EXTENSIONS}
    return {**result, 'state': row.state, 'documents': documents}
