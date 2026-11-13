"""What came back from the client as files, for the Board's To review lane (plan.md §8.8; L9, L125, L135; slice 59).
Reads only, a fixed number of queries.

- `read_rows(deal)`: a To review row per staged read a client's upload started (L135): "Their census file was read"
  with "Review and apply ▸", which opens the census import it staged on the Census tab (`?import=`), or the intake
  read in Work with Claude on the Intake tab (`?claude=1`), where "Use this scan ▸" applies it. Without the row a
  client's census would sit read but unapplied while the Advisor kept its typed counts (need 6).
- `files(deal)`: the client's files nobody has accepted or marked wrong yet, newest first (at most `SHOWN`): each by
  the slot it answered and when it came — never its name, which is often the people's (file names are PHI, §3.8; the
  Documents tab opens it) — with the reader "Read with Claude ▸" would start for it (`reader`: a renewal or a quote
  goes to the quote reader, a paper questionnaire to the questionnaire's, L125, G101) and where its read stands
  (`read`: reading, waiting, used, or '').
"""

from ai import file_reads
from census.models import CensusImport
from documents import kinds as document_kinds
from documents.models import Document

from ..portal.asked import PAPER
from ..portal.files_part import CENSUS_SLOT
from ..portal.files_part import label as slot_label

SHOWN = 8
REVIEW_AND_APPLY = 'Review and apply ▸'
SECTIONS = {'census': 'Census', 'intake': 'Intake'}


def _what(kind, count):
    """The file a read row names: "census file", "current invoice", "files"."""
    if count != 1:
        return f'{count} files'
    if kind == 'census':
        return 'census file'
    text = document_kinds.label(kind) if kind != 'other' else 'file'
    return text[:1].lower() + text[1:]


def read_rows(deal):
    reads = file_reads.client_reads([deal.id]).get(deal.id, [])
    if not reads:
        return []
    ids = [document_id for read in reads for document_id in read['documents']]
    kinds = dict(Document.all_objects.filter(deal=deal, pk__in=ids).values_list('id', 'kind'))
    imports = dict(
        CensusImport.objects.filter(job_id__in=[read['job_id'] for read in reads], status=CensusImport.PROPOSED)
        .order_by('id')
        .values_list('job_id', 'id')
    )
    rows = []
    for read in reads:
        count = len(read['documents'])
        first = kinds.get(read['documents'][0], '') if count else ''
        if read['target'] == 'census':
            fix = {'tab': 'census', 'params': {'import': imports.get(read['job_id'])}}
        else:
            fix = {'tab': read['target'], 'params': {'claude': '1'}}
        rows.append(
            {
                'key': f'read:{read["job_id"]}',
                'surface': read['target'],
                'section': SECTIONS.get(read['target'], read['target'].title()),
                'count': 1,
                'questions': 0,
                'label': f'Their {_what(first, count)} {"was" if count == 1 else "were"} read',
                'detail': read['summary'],  # counts only: "Mapped 6 of 6 census columns: waiting on the Census tab"
                'action': REVIEW_AND_APPLY,
                'fix': fix,
            }
        )
    return rows


def _label(document):
    if document.slot == CENSUS_SLOT:
        return 'Census file'
    if document.slot.startswith(PAPER):
        return f'{document_kinds.label(document.kind)} — paper copy'
    return slot_label(document.slot) if document.slot else document_kinds.label(document.kind)


def files(deal):
    """([file row], how many more) for the Documents row of the To review lane."""
    # newest first, by id: the container's clock can step back (never order by a timestamp)
    rows = Document.objects.filter(deal=deal, source='client', review_state='').order_by('-id')
    found = list(rows.only('id', 'kind', 'slot', 'uploaded_at')[: SHOWN + 1])
    total = rows.count() if len(found) > SHOWN else len(found)
    stand = file_reads.where_reads_stand(deal.id) if found else {}
    out = [
        {
            'id': document.id,
            'label': _label(document),
            'at': document.uploaded_at.isoformat(),
            'reader': file_reads.reader_for(document.kind),
            'read': stand.get(document.id, ''),
        }
        for document in found[:SHOWN]
    ]
    return out, total - len(out)
