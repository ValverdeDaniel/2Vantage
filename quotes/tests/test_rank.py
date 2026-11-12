"""⚖ Rank plans through the star rule on GD1 (plan.md §5.4, §7.5, §10.4; D6, D36, D96, D97, F111, OQ44; Q.9 row 37:
skips curated lines, stays within `room()`, needs guidance, writes with Undo). Claude is the fake client: its answer is
scripted, the door, the job, the star rule and the landing are the real ones. Writes roll back with each test."""

import pytest

from ai.models import DealAi, Job
from deals.models import Activity
from intake.services import update_answers
from quotes import presented
from quotes.models import Plan
from quotes.rank import rules
from quotes.rank.job import rank_key
from quotes.rank.start import after_read
from quotes.selectors.state import line_state
from quotes.shapes import LineData, PlanData

pytestmark = pytest.mark.django_db

GUIDANCE = '- Stay under $45,000 a month for medical\n- Keep an HSA-compatible HDHP\n- Broad PPO network for families'


def guide(user, deal, text=GUIDANCE):
    update_answers(user, deal.id, {'client_guidance': text})


def answer(fake, line, ids, reason='Fits the budget and keeps the network'):
    fake.record(
        rank_key(line), {'shortlist': [{'plan_id': pid, 'reason': f'{reason} ({n})'} for n, pid in enumerate(ids)]}
    )


def rank(api, deal, **body):
    return api.post(f'/api/deals/{deal.id}/ai/rank/', {'line': 'medical', **body}, format='json')


def stars(deal):
    return {plan.id: plan.star_reason for plan in Plan.objects.filter(deal=deal, line='medical', starred=True)}


# ---- the pure rule -------------------------------------------------------------------------------------------------
def _line():
    plans = [PlanData(1, 'current', 'Aetna', 'PPO'), PlanData(2, 'alternate', 'Cigna', 'HMO', starred=True)]
    plans += [PlanData(n, 'alternate', 'Cigna', f'Q{n}') for n in range(3, 22)]
    return LineData('tiered', plans, key='medical')


def test_D96_choose_takes_claudes_order_at_most_eight_and_never_a_current_plan():
    line = _line()
    picks = [(1, 'current'), (5, 'a'), (5, 'again'), (999, 'not here'), *[(n, 'b') for n in range(6, 16)]]
    chosen, left = rules.choose(line, picks, rules.scope(line))
    assert [pid for pid, _why in chosen] == [5, 6, 7, 8, 9, 10, 11, 12] and left == []


def test_D96_choose_stops_at_the_lines_room():
    line = _line()
    starred = LineData('tiered', [*line.plans[:6], *[PlanData(n, 'alternate', starred=True) for n in range(30, 42)]])
    ids = rules.scope(starred, among=[3, 4, 5, 6])  # a filtered board: the 13 stars outside it stay (OQ44)
    assert presented.room(rules.cleared(starred, ids)) == 2
    chosen, left = rules.choose(starred, [(4, 'a'), (5, 'b'), (6, 'c')], ids)
    assert ([pid for pid, _why in chosen], left) == ([4, 5], [6])


def test_D96_curated_names_why_a_line_is_left_alone():
    plain = LineData('tiered', [PlanData(1, 'current'), PlanData(2, 'alternate')])
    assert rules.curated(plain) == ''
    assert rules.curated(LineData('tiered', [PlanData(2, 'alternate', starred=True)])) == 'starred plans'
    assert rules.curated(LineData('tiered', [PlanData(2, 'alternate', sold=True)])) == 'a sold plan'
    assert rules.curated(LineData('tiered', [PlanData(2, 'renewal', recommended=True)])) == 'a recommended plan'


def test_D96_a_long_reason_is_cut_at_a_word_to_fit_the_star():
    cut = rules.reason('word ' * 40)
    assert len(cut) <= rules.REASON_LENGTH and cut.endswith('…') and ' wor…' not in cut


def test_D96_Q3_rank_write_path(user):
    from conftest import make_deal, write_path_contract
    from quotes import services
    from quotes.services.rank import rank as rank_service

    deal = make_deal(user)
    services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='HMO 1500')
    quote = services.create_plan(user, deal, line='medical', role='alternate', carrier='Cigna', name='Open Access')
    write_path_contract(
        user,
        quote,
        call=lambda: rank_service(user, deal, 'medical', [(quote.id, 'Lowest premium with the HMO network')]),
        read=lambda plan: (plan.starred, plan.star_reason),
        later=lambda: services.star(user, deal, [quote.id], False),
    )


# ---- the door, the job and the landing on GD1 ------------------------------------------------------------------------
def test_F111_without_guidance_rank_says_add_client_guidance_first(api, gd1, fake_claude):
    answer_ = rank(api, gd1.deal)
    assert answer_.status_code == 409 and answer_.json()['detail'].startswith('Add client guidance first')
    assert not Job.objects.filter(deal=gd1.deal, kind='rank').exists() and fake_claude.log == []


def test_D96_F111_rank_stars_five_to_eight_with_reasons_within_room_and_undo_puts_them_back(
    api, user, gd1, fake_claude
):
    deal, refs = gd1.deal, gd1.refs
    guide(user, deal)
    before = stars(deal)
    named = [refs[ref] for ref in ('U1', 'CG2', 'CG3', 'U3', 'FB1', 'FB2', 'D1', 'CG4', 'U5')]
    answer(fake_claude, 'medical', [refs['A'], *named])  # a current plan named first: it takes no star

    started = rank(api, deal)

    assert started.status_code == 201
    job = Job.objects.get(pk=started.json()['id'])
    assert (job.kind, job.lane, job.status, job.land, job.resolution) == ('rank', 'work', 'done', 'auto', 'applied')
    ranked = stars(deal)
    assert set(ranked) == set(named[:8])  # eight at most, in Claude's order; every hand-picked star replaced
    assert all(reason.startswith('Fits the budget') for reason in ranked.values())
    assert presented.columns(line_state(deal, 'medical').data) <= presented.MAX_COLUMNS
    sent = fake_claude.log[-1]['params']
    assert sent['output_config']['format']['type'] == 'json_schema' and 'tool_choice' not in sent
    text = sent['messages'][0]['content'][0]['text']
    assert 'HSA-compatible HDHP' in text and 'At most 8 plans fit' in text
    row = Activity.objects.get(pk=job.activity_id)
    assert row.actor_kind == 'claude' and row.summary.startswith('Ranked the Medical plans')

    news = api.get(f'/api/deals/{deal.id}/ai/').json()['news']
    assert [(n['kind'], n['job_id'], n['summary']) for n in news] == [('rank', job.id, 'starred 8 Medical plans')]
    undone = api.post(f'/api/ai/jobs/{job.id}/undo/', {}, format='json')
    assert undone.status_code == 200 and stars(deal) == before  # hand-picked stars and their reasons are back


def test_OQ44_rank_filtered_replaces_stars_among_the_shown_plans_only(api, user, gd1, fake_claude):
    deal, refs = gd1.deal, gd1.refs
    guide(user, deal)
    shown = [refs[ref] for ref in ('CG2', 'U3', 'U1', 'CG3')]
    outside = {pid: why for pid, why in stars(deal).items() if pid not in shown}
    answer(fake_claude, 'medical', [refs['U3'], refs['CG2'], refs['U5']])  # U5 is outside the filter: never starred

    job = rank(api, deal, plan_ids=shown).json()

    after = stars(deal)
    assert job['status'] == 'done' and {pid: after[pid] for pid in outside} == outside  # hand-picked stars stay
    assert set(after) - set(outside) == {refs['U3'], refs['CG2']}  # U1 and CG3 lost theirs to the ranking
    assert (
        'Rank only within this producer-filtered subset'
        in fake_claude.log[-1]['params']['messages'][0]['content'][0]['text']
    )


def test_D96_rank_never_passes_room_and_says_what_was_left_out(api, user, gd1, fake_claude):
    deal, refs = gd1.deal, gd1.refs
    guide(user, deal)
    shown = [refs[ref] for ref in ('CG2', 'U3', 'A2', 'B2', 'U1')]  # GD1's Medical holds 14 columns: room 2, +1 (U1)
    answer(fake_claude, 'medical', shown)

    job = Job.objects.get(pk=rank(api, deal, plan_ids=shown).json()['id'])

    assert presented.room(line_state(deal, 'medical').data) == 0
    assert {refs['CG2'], refs['U3'], refs['A2']} <= set(stars(deal)) and refs['B2'] not in stars(deal)
    assert job.result['landed']['skipped'] == ['2 more were left out: the Medical proposal is full.']


def test_D104_a_locked_table_refuses_rank(api, user, gd1, fake_claude):
    guide(user, gd1.deal)
    DealAi.objects.create(deal=gd1.deal, locked_by=user, locked_at='2026-11-12T10:00:00Z')
    refused = rank(api, gd1.deal)
    assert refused.status_code == 409 and 'locked from Claude' in refused.json()['detail']


@pytest.mark.parametrize('body', [{'line': 'nope'}, {'plan_ids': ['x']}, {'plan_ids': [0]}])
def test_F111_rank_reads_its_line_and_ids_or_answers_400(api, user, gd1, fake_claude, body):
    guide(user, gd1.deal)
    assert rank(api, gd1.deal, **body).status_code == 400


def test_D96_an_answer_naming_no_plan_of_the_line_fails_and_writes_nothing(api, user, gd1, fake_claude):
    guide(user, gd1.deal)
    before = stars(gd1.deal)
    answer(fake_claude, 'medical', [gd1.refs['DN2'], 999999])
    job = rank(api, gd1.deal).json()
    assert job['status'] == 'failed' and 'named no quoted plan of Medical' in job['error']
    assert stars(gd1.deal) == before


# ---- the rank after a read (D96, Q.9 row 37: curated lines are skipped) ---------------------------------------------
def test_D96_a_read_that_adds_quotes_ranks_an_uncurated_line(
    user, quote_first, fake_claude, django_capture_on_commit_callbacks
):
    deal = quote_first.built.deal
    guide(user, deal)
    quotes = list(Plan.objects.filter(deal=deal, line='medical').values_list('id', flat=True))[:6]
    read = Job.objects.create(deal=deal, lane='work', kind='read', target='quotes', created_by=user, status='done')
    answer(fake_claude, 'medical', quotes)

    with django_capture_on_commit_callbacks(execute=True):
        after_read(user, deal, read, {'created': quotes})

    ranked = Job.objects.get(deal=deal, kind='rank')
    assert ranked.params['after_read'] == read.id and ranked.resolution == 'applied'
    assert set(stars(deal)) == set(quotes)


def test_D96_a_read_leaves_a_curated_line_alone(user, quote_first, fake_claude, django_capture_on_commit_callbacks):
    from quotes.services import star

    deal = quote_first.built.deal
    guide(user, deal)
    quotes = list(Plan.objects.filter(deal=deal, line='medical').values_list('id', flat=True))[:3]
    star(user, deal, quotes[:1], True)  # someone chose on Medical already
    read = Job.objects.create(deal=deal, lane='work', kind='read', target='quotes', created_by=user, status='done')

    with django_capture_on_commit_callbacks(execute=True):
        after_read(user, deal, read, {'created': quotes})

    assert not Job.objects.filter(deal=deal, kind='rank').exists() and fake_claude.log == []


def test_D91_a_refused_rank_fails_in_words_for_a_producer(api, user, gd1, fake_claude):
    guide(user, gd1.deal)
    fake_claude.record(rank_key('medical'), {'shortlist': []}, fault='refusal')
    job = rank(api, gd1.deal).json()
    assert job['status'] == 'failed' and job['error'].startswith('Claude could not rank these plans')


def test_D91_a_rank_sonnet_refuses_is_tried_once_on_opus_for_an_admin(admin_api, admin_user, gd1, fake_claude):
    from ai import pricing

    guide(admin_user, gd1.deal)
    picks = [{'plan_id': gd1.refs[ref], 'reason': 'Fits'} for ref in ('U1', 'CG2', 'CG3', 'U3', 'CG4')]
    fake_claude.record(rank_key('medical'), {'shortlist': picks}, fault='refusal', fault_on=pricing.SONNET)
    job = rank(admin_api, gd1.deal).json()
    assert (job['status'], job['model']) == ('done', pricing.OPUS)
    assert [entry['params']['model'] for entry in fake_claude.log] == [pricing.SONNET, pricing.OPUS]
