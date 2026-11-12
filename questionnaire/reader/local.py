"""What the questionnaire reader settles before Claude reads (plan.md §10.4, §10.8; G99; slice 52): the Reader's
`local` hook.

Nothing is read in code here; the hook only refuses a read that could not be used, before it costs anything (the old
reader's first check: "The questionnaire is already signed — nothing was changed."): a file whose kind has no form on
the deal, or whose form is signed. A filled form is what the reader reads, medical answers and all, so the member-data
screen never leaves its pages out (§10.8; the reader registers only behind the PHI gate, as the census's does).
"""

from ai.progress import JobFailed
from deals.models import Deal

from ..selectors import context
from . import which


def local(job, progress, files):
    """(the files Claude reads, None); raises JobFailed with the reason a read cannot go into its form."""
    progress.step('Finding the form each file fills', 3)
    ctx = context.deal_context(Deal.objects.get(pk=job.deal_id))
    for file in files:
        refused = which.refusal(ctx, file.kind)
        if refused:
            raise JobFailed(refused)
        file.screened = ()  # a filled form's pages are what it reads
    return files, None
