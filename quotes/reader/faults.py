"""Named faults for the fake client (plan.md §12.8; Q.6): a corpus case's perfect answer bent the way a read goes
wrong, so tests and the Eval scorer see each mistake cost what it should. Faults of the call itself (truncation,
refusal, a silent stream, Stop mid-range) are the fake transport's (ai/testing.py); these are faults of the answer."""

import copy

FAULTS = ('starred_rate', 'missed_link', 'invented_plan', 'blank_cell')


def faulty(case, fault):
    """The perfect answer bent by one named fault: "$512.34*" in a rate, a missed renewal link, an invented plan or
    a blank cell."""
    answer = copy.deepcopy(case.answer)
    block = answer['lines'][0]
    if fault == 'starred_rate':
        rate = next(row for row in block['rows'] if row['key'] == 'rate_ee')
        rate['cells'][0]['value'] = '$' + rate['cells'][0]['value'] + '*'
    elif fault == 'missed_link':
        for column in block['columns']:
            column['renews_col'] = -1
    elif fault == 'invented_plan':
        block['columns'].append(
            {**block['columns'][0], 'col': 99, 'plan_name': 'Invented Plan 9999', 'plan_number': '', 'codes': []}
        )
    elif fault == 'blank_cell':
        rate = next(row for row in block['rows'] if row['key'] == 'rate_es')
        rate['cells'] = rate['cells'][1:]
    else:
        raise ValueError(f'Unknown fault: {fault}')
    return answer
