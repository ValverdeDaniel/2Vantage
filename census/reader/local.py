"""What the census reader reads in code before Claude reads the rest (plan.md §5.3.2, §10.4, §10.8; C11–C15, D109;
slice 51): the census Reader's `local` hook.

A census spreadsheet sent to Claude is not read by Claude (the old app's rule: "a tabular census keeps its
mapping-review step"): the importer reads it (C12, C13), the offline mapper proposes its columns (C14) — starting from
a person's own choices when the same file already waits on the Census tab — and the mapping assist proposes the
columns it left unmapped or doubted from their shapes only (D109). It waits as a proposed import for the mapping
dialog. PDF pages and pictures go on to Claude, whole: the census reader reads people, so the member-data screen never
leaves its pages out (§10.8; it registers only behind the PHI gate).
"""

from ai.progress import JobFailed
from documents import kinds as document_kinds

from ..importer import CensusFileError, open_table
from ..importer import mapping as mapper
from ..models import CensusImport
from . import assist


def _opened(job, file):
    """(the file's table, the mapping to start from): a person's choices when this file already waits, else the
    offline mapper's."""
    name = f'census{file.extension}'  # never the file's own name (§3.8)
    waiting = (
        CensusImport.objects.filter(deal_id=job.deal_id, document_id=file.id, status=CensusImport.PROPOSED)
        .order_by('-id')
        .first()
    )
    if waiting is not None and 'keys' not in (waiting.read or {}):
        found = open_table(
            name,
            file.raw,
            sheet=waiting.sheet_name or None,
            header_row=waiting.header_row,
            first_data_row=waiting.first_data_row,
            reformat=not (waiting.pivot or {}).get('declined'),
        )
        if found.table.headers == waiting.headers:
            return found, waiting.mapping
    found = open_table(name, file.raw)
    return found, mapper.propose(found.table.headers)


def local(job, progress, files):
    """(the files Claude reads, what was done here or None)."""
    from ..services.reads import stage_sheet

    for_claude, imports, assisted, findings = [], [], 0, []
    for file in files:
        if file.shape != document_kinds.SHEET:
            file.screened = ()  # a roster's pages are what it reads
            for_claude.append(file)
            continue
        progress.step('Reading the census spreadsheet', 5)
        try:
            found, base = _opened(job, file)
        except CensusFileError as exc:  # the sentence never names the file
            findings.append({'text': str(exc), 'hard': False})
            continue
        mapping, count, finding = assist.ask(job, file, found.table, base, progress)
        imp = stage_sheet(job.created_by, job.deal_id, job.id, file.id, found, mapping, count)
        imports.append(imp.id)
        assisted += count
        if finding:
            findings.append({'text': finding, 'hard': False})
    if not imports and not for_claude and findings:
        raise JobFailed(findings[0]['text'])
    if not imports and not findings:
        return for_claude, None
    return for_claude, {'imports': imports, 'assisted': assisted, 'findings': findings}
