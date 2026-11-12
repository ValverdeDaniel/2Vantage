"""The bytes of one packet row (plan.md §9.8–§9.11; K51, K55, K63; rule 10). Every door — a row's own download, the
packet zip and a draft's `.eml` — builds through here, so a file that cannot be built is refused the same way
everywhere: `NotBuilt` names the row's label and nothing else, never the exception's text (bug 36: it can carry a
member's value).

- Census files and Warner's forms are built from the request (`formats.fill`, `forms.fill`), the cover drawn
  (`cover.page`); questionnaires come from the questionnaire app: the filed signed copy once the officer has signed
  (G135), an accepted paper copy, else the DRAFT built now; documents are read from their own files.
- Names: `<Client> - <Carrier> census.xlsx`, `<Client> - Quote request form….xlsx`, `<Client> - RFP cover page.pdf`, the
  questionnaire's own `<client>-<form>.pdf`; a document keeps its name unless it carries member data, which takes
  documents' `<Client> - <Kind>.<ext>` (`documents.services.access.download_name`) — no person's name, ever.
"""

from collections import namedtuple

from documents.models import Document
from documents.services import access
from questionnaire.pdf import acroform, build, fonts, stamp_draw
from questionnaire.selectors import files as questionnaire_files

from .cover import page as cover
from .formats import fill as census_fill
from .forms import fill as form_fill
from .xlsx.refs import FillError

Member = namedtuple('Member', 'name title data phi document')
FAILURES = (
    FillError,
    census_fill.NoCensus,
    census_fill.UnknownFile,
    acroform.AcroFormError,
    stamp_draw.StampError,
    build.BuildError,
    fonts.FontMissing,
    OSError,
    ValueError,
)
NOT_BUILT = '“{label}” could not be built, so nothing was downloaded. Fix it or untick it, then try again.'


class NotBuilt(Exception):
    """A row whose file could not be built: 409 naming its label only."""

    def __init__(self, label):
        super().__init__(label)
        self.label = label
        self.sentence = NOT_BUILT.format(label=label)


def _document(ctx, document_id):
    found = Document.objects.select_related('deal__client').filter(deal_id=ctx.deal.id, pk=document_id).first()
    if found is None or not found.file:
        raise FileNotFoundError(document_id)
    with found.file.open('rb') as handle:
        return found, handle.read()


def _questionnaire(ctx, row):
    if row['copy'] == 'paper' and row['document']:
        found, data = _document(ctx, row['document'])
        return access.download_name(found), data, found.id
    copy = questionnaire_files.download(ctx.deal, row['form'])
    return copy.name, copy.data, copy.document.id if copy.document else None


def _build(ctx, row):
    key, section = row['key'], row['section']
    if section == 'census':
        built = census_fill.build(ctx.deal, key.removeprefix('census-'), people=ctx.people)
        return built.filename, built.content, None
    if section == 'census_forms':
        built = form_fill.build(ctx, row['variant'], census=True)
        return built.filename, built.content, None
    if key == 'form':
        built = form_fill.build(ctx, ctx.variant)
        return built.filename, built.content, None
    if key == 'cover':
        return cover.filename(ctx), cover.build(ctx), None
    if section == 'questionnaires':
        return _questionnaire(ctx, row)
    if row.get('document'):
        found, data = _document(ctx, row['document'])
        return access.download_name(found), data, found.id
    raise FileNotFoundError(key)


def member(ctx, row):
    """Member(file name, title, bytes, carries member data, document id). Raises NotBuilt."""
    try:
        name, data, document = _build(ctx, row)
    except FAILURES as error:
        raise NotBuilt(row['title']) from error
    return Member(name, row['title'], data, bool(row.get('phi')), document)


def members(ctx, rows):
    """[Member] for the rows, in order, with repeated names suffixed " (2)", " (3)" (two files can share a name)."""
    out, used = [], {}
    for row in rows:
        found = member(ctx, row)
        name = found.name
        if name in used:
            used[name] += 1
            stem, dot, ext = name.rpartition('.')
            name = f'{stem} ({used[found.name]}).{ext}' if dot else f'{name} ({used[found.name]})'
        else:
            used[name] = 1
        out.append(found._replace(name=name))
    return out
