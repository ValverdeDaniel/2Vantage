"""The `recheck` job: Claude reads flagged values again against their pages (plan.md §10.4; D40, D93, E77; slice 22;
the old ai/flag_check.py and scan_audit.audit_claims at 891f1b3).

One check mode (D93): for each value the owner names (`registry.checkers`, its open warnings with a file), Claude
says whether the file supports it (agree), prints something else (a fix) or does not show it (not found). Each file
is read only where its values were recorded: a PDF's claims ride the pages they name, so a 300-page proposal with
flags on four pages sends four pages; a value with no page rides the whole file only when the file is short, else it
is listed as not checked. At most 40 claims go in one call; verdicts across calls keep the best (agree beats a fix,
a fix beats not found). The owner builds the change set, and it always waits for a person: Claude never approves or
fixes a value by itself (D-119; OQ28). Steps, errors and the change set never carry a file name or a file's text.
"""

from decimal import Decimal

from django.conf import settings

from documents.models import Document

from . import budget, calls, client, content, recheck_prompt, registry
from .models import Job
from .progress import JobFailed
from .read_files import from_documents, plan
from .reading import model_for

CLAIMS_PER_CALL = 40  # each comes back as one verdict, and a reply has a length limit
MAX_UNPAGED_PDF_PAGES = 30  # a value with no page rides a PDF only this long; past it, re-reading is not a re-check
RANK = {'not_found': 0, 'differs': 1, 'agree': 2}

NOTHING = 'Those flags were cleared before the re-check began, so there is nothing to re-check.'
NO_CHECKER = 'Nothing re-checks these values yet.'
NO_PAGE = 'no page was recorded for it in a long file'
FAILED = {'missing': 'its file is no longer stored', 'unreadable': "its file can't be opened"}
NOT_ASKED = 'Claude could not check it: {why}'
CAP = 'the re-check reached its cost cap first'


def _better(held, new):
    return new if held is None or RANK.get(new['verdict'], 0) > RANK.get(held['verdict'], 0) else held


def _verdict(raw):
    page = raw.get('page')
    return {
        'verdict': raw.get('verdict') if raw.get('verdict') in RANK else 'not_found',
        'found_value': str(raw.get('found_value') or '')[:300],
        'page': page if isinstance(page, int) and page > 0 else None,
        'confidence': raw.get('confidence') if raw.get('confidence') in recheck_prompt.CONFIDENCES else 'low',
        'note': str(raw.get('note') or '')[:300],
    }


class Check:
    def __init__(self, job, progress):
        self.job, self.progress = job, progress
        self.model, self.effort = model_for(job), settings.AI_EFFORT.get('recheck', 'high')
        self.verdicts, self.unverified, self.spent, self.calls = {}, {}, Decimal(0), 0
        self.halted = ''

    def skip(self, claims, why):
        for claim in claims:
            self.unverified.setdefault(claim['ref'], why)

    def parts(self, file, claims):
        """[(range, claims on it)] for one file: a PDF only on the pages its claims name."""
        pdf = file.extension == '.pdf'
        unpaged = [claim for claim in claims if not claim.get('page')]
        if pdf and unpaged and (file.document.page_count or 0) > MAX_UNPAGED_PDF_PAGES:
            self.skip(unpaged, NO_PAGE)
            claims, unpaged = [claim for claim in claims if claim.get('page')], []
        if not claims:
            return []
        only = sorted({claim['page'] for claim in claims}) if pdf and not unpaged else None
        ranges, _out, failure = plan(file, max_tokens=client.MAX_TOKENS, only_pages=only)
        if failure:
            self.skip(claims, FAILED.get(failure['reason'], FAILED['unreadable']))
            return []
        out = []
        for part in ranges:
            here = [c for c in claims if part.kind != 'pdf' or not c.get('page') or c['page'] in part.pages]
            if here:
                out.append((part, here))
        return out

    def ask(self, file, part, claims, number):
        note = recheck_prompt.claims_note(claims)
        params = client.request(
            model=self.model,
            system=recheck_prompt.PROMPT,
            content=content.blocks(file, part, note),
            schema=recheck_prompt.SCHEMA,
            effort=self.effort,
        )
        tokens_in, _ = budget.range_tokens(part.est_input, 60 * len(claims))
        prompt = int(len(recheck_prompt.PROMPT + note) / budget.CHARS_PER_TOKEN)
        planned = calls.Planned(params, ('recheck', file.hash, f'{part.label}#{number}'), tokens_in + prompt)
        try:
            done = calls.extract(planned, job=self.job, deal_id=self.job.deal_id, purpose='recheck')
        except budget.OverLimit as exc:
            self.halted = exc.sentence
            self.skip(claims, CAP)
            return
        self.calls += 1
        self.spent += done.cost or 0
        if done.error is not None:
            self.skip(claims, done.error.reason)
            return
        wanted = {claim['ref'] for claim in claims}
        for raw in (done.data or {}).get('checks') or []:
            ref = str(raw.get('ref') or '')
            if ref in wanted:
                self.verdicts[ref] = _better(self.verdicts.get(ref), _verdict(raw))

    def run(self, claims):
        by_doc = {}
        for claim in claims:
            by_doc.setdefault(claim['doc'], []).append(claim)
        found = list(Document.all_objects.filter(deal_id=self.job.deal_id, pk__in=list(by_doc)))
        files, failed = from_documents(found)
        for failure in failed:
            self.skip(by_doc.get(failure['doc'], []), FAILED.get(failure['reason'], FAILED['unreadable']))
        for doc in set(by_doc) - {document.id for document in found}:
            self.skip(by_doc[doc], FAILED['missing'])
        work = [(file, part, rows) for file in files for part, rows in self.parts(file, by_doc[file.id])]
        total = sum((len(rows) + CLAIMS_PER_CALL - 1) // CLAIMS_PER_CALL for _file, _part, rows in work) or 1
        number = 0
        for file, part, rows in work:
            for start in range(0, len(rows), CLAIMS_PER_CALL):
                number += 1
                batch = rows[start : start + CLAIMS_PER_CALL]
                if self.halted:
                    self.skip(batch, CAP)
                    continue
                words = f'Checking {len(batch)} value{"s" if len(batch) != 1 else ""} on {part.where()}'
                self.progress.say(words, 5 + 85 * (number - 1) / total)
                self.ask(file, part, batch, number)
                if not self.halted and budget.over_run_cap(self.spent):
                    self.halted = f'This re-check reached its ${budget.run_cap():,.2f} cap; what it finished is kept.'


def run(job, progress):
    """The job's runner: the owner's change set (Job.result), always waiting for a person (`landing.on_recheck`)."""
    checker = registry.checkers.get(job.target)
    if checker is None:
        raise JobFailed(NO_CHECKER)
    params = job.params or {}
    scope = {'refs': params.get('refs') or [], **({'scanned': True} if params.get('scanned') else {})}
    claims = checker.claims(job.deal, scope)  # the values still as they were asked about (Overview's: unapproved)
    if not claims:
        raise JobFailed(NOTHING)
    count, what = len(claims), 'scanned' if params.get('scanned') else 'flagged'
    progress.step(f'Re-checking {count} {what} value{"s" if count != 1 else ""} against their files', 3)
    check = Check(job, progress)
    check.run(claims)
    Job.objects.filter(pk=job.pk).update(model=check.model)
    progress.step('Proposing what to approve and what to fix', 95)
    unverified = {ref: NOT_ASKED.format(why=why) for ref, why in check.unverified.items() if ref not in check.verdicts}
    extra = {'model': check.model, 'cost_usd': f'{check.spent:.4f}', 'halted': check.halted}
    return checker.build_changes(job.deal, claims, check.verdicts, {**extra, 'not_asked': unverified})
