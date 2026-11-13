"""The enrollment track (I49–I52; plan.md §5.9, N.2): the census, mapped and imported, its errors, and the client's
values and questions waiting on us. It keeps leading after quotes are in, so a census that arrives late is mapped and
picked up (ch. 4). On a quote-first deal (OQ90):
- "Import the census" does not lead while typed tier counts price every plan (I50, I.5 bug 19);
- once quotes are in and some plan has no enrollment to price it, the step leads as "Add the census, or type
  enrollment in the Advisor", opening the Advisor's tier counts, with the Census tab beside it.
After the sale the census steps leave (implementation is deferred) and the client's values and questions stay, never
leading, so the commission step leads (§5.9). Words from old Vantage 891f1b3 `tasks/steps.py`. Pure.
"""

from .. import rules
from . import asked
from .base import Steps
from .situation import raw_out

ADD_OR_TYPE = 'Add the census, or type enrollment in the Advisor'


def add(s: Steps, facts, sit):
    census = facts.get('census') or {}
    review = facts.get('review') or {}
    if not sit.sold and (census.get('employees') or 0) + (census.get('dependents') or 0) == 0:
        _empty(s, facts, census, sit)
    errors = census.get('errors') or 0
    if errors and not sit.sold:
        s.add('fix_census', f'Fix {rules.plural(errors, "census error")}', severity='error')
    pending = review.get('pending') or {}
    intake_shown = sit.marketed_at is None and not sit.sold and bool(facts.get('intake'))
    census_values = (pending.get('census') or 0) + (pending.get('people') or 0)
    values = census_values + (0 if intake_shown else pending.get('intake') or 0)
    if values:
        section = 'census' if census_values else 'intake'
        s.add('approve_client', f'Review {rules.plural(values, "client-provided value")}', severity='warn',
              params={'view': 'queue', 'section': section}, lead=not sit.sold)  # fmt: skip
    questions = review.get('questions') or {}
    if questions.get('open'):
        n = questions['open']
        s.add('answer_client_questions', f'Answer {rules.plural(n, "question")} from the client', severity='warn',
              since=questions.get('oldest_at'))  # fmt: skip


def _empty(s, facts, census, sit):
    """An empty roster: review the mapping, map the file, wait on the client, or import one."""
    if census.get('proposed_import'):
        s.add('review_mapping', 'Review column mapping', severity='warn', params={'import': census['proposed_import']})
        return
    if census.get('files'):
        s.add('map_census', 'Map the census')
        return
    quote_first = sit.quotes_in and sit.unpriced
    lead = not sit.typed_drives
    if asked.census_file(raw_out(sit)):
        s.add('import_census', 'Waiting on the client for the census', state='waiting', owner='client', lead=lead)
    elif quote_first:
        line = ((facts.get('quotes') or {}).get('unpriced_lines') or [''])[0]
        s.add('import_census', ADD_OR_TYPE, tab='advisor', params={'line': line} if line else None,
              severity='warn', also={'tab': 'census', 'label': 'Census ▸'})  # fmt: skip
    else:
        s.add('import_census', 'Import the census', lead=lead)
