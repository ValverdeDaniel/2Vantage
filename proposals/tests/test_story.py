"""The client deck's story (plan.md §9.5; J123–J138, J165; Q.9 row 29: story cases, firm pages print nothing until
written). GD1's Facts, read once a test, then varied as a dict: the story is pure over its Facts."""

import copy

import pytest

from proposals.layout import flowables, furniture, items, tokens
from proposals.layout import table as tb
from proposals.story import build, facts, glance, recommend, sequence

pytestmark = pytest.mark.django_db

FIRM = {
    'about': 'We place benefits for manufacturers across the state, and we answer the phone.',
    'stats': [{'value': '20+', 'label': 'Years of experience', 'note': ''}, {'value': '300', 'label': 'Clients'}],
    'calendar': [{'meeting': 'Kick-off', 'topics': ['Review last year', 'Set goals'], 'when': 'January'}],
}
PERSON = {
    'id': 1,
    'name': 'Rosa Example',
    'title': 'Account manager',
    'group': 'Service',
    'phone': '555-0100',
    'email': 'rosa@example.com',
    'bio': '',
    'photo': '',
}


@pytest.fixture
def found(gd1):
    return facts.facts(gd1.deal)


def titles(story):
    out = []
    for page in story:
        for flowable in page:
            if isinstance(flowable, flowables.Title | flowables.FullPage):
                out.append(flowable.text if isinstance(flowable, flowables.Title) else f'[{flowable.title}]')
                break
    return out


def written(found, team=1, bios=False):
    found = copy.deepcopy(found)
    found['firm'] = copy.deepcopy(FIRM)
    found['team'] = [
        dict(PERSON, id=n, name=f'Person {n}', bio='Twenty years in benefits.' if bios else '') for n in range(team)
    ]
    found['experience'] = {
        'summary': 'Claims ran under premium.',
        'rows': [{'period': '2025', 'premium': '$410,000', 'claims': '$298,000', 'ratio': '72.7%'}],
    }
    found['next_steps'] = [{'date': '2026-12-01', 'text': 'Decide on the medical plan'}]
    return found


def test_J123_J124_GD1_opens_on_its_cover_and_closes_with_thank_you_and_important_information(found):
    story = sequence.story(found)
    names = titles(story)
    assert names[0] == '[Golden Manufacturing (synthetic)]'
    assert names[-2:] == ['[Thank you]', 'Important information']
    assert 'Our recommendation at a glance' in names
    assert '[Agenda]' not in names  # two sections only: no agenda, no dividers


def test_J123_the_cover_says_what_who_when_and_by_whom(found):
    cover = sequence.story(found)[0][0]
    text = ' '.join(items.plain(item) for item in cover.items if item['t'] == 'text')
    assert 'Golden Manufacturing (synthetic)' in text
    assert '2027 Benefits Proposal' in text
    assert 'Coverage effective January 1, 2027' in text
    assert f'by {found["prepared_by"]}' in text and found['prepared_by']
    assert 'Draft for review, not for clients' in text  # every file not yet issued (OQ35)
    titled = copy.deepcopy(found)
    titled['title'] = 'Renewal options for 2027'
    retitled = sequence.story(titled)[0][0]
    assert 'Renewal options for 2027' in ' '.join(items.plain(i) for i in retitled.items if i['t'] == 'text')


def test_J124_agenda_and_dividers_print_together_only_when_framed(found):
    full = written(found)
    names = titles(sequence.story(full))
    assert names[1] == '[Agenda]'
    dividers = [
        name
        for name in names
        if name in ('[About Vantage Risk Solutions]', '[How we got here]', '[Your coverage]', '[What happens next]')
    ]
    assert len(dividers) == 4
    off = copy.deepcopy(full)
    off['pages']['agenda'] = False
    assert '[Agenda]' not in titles(sequence.story(off))
    assert sequence.sections_of(found) and len(sequence.sections_of(found)) < 3


def test_J125_J138_firm_pages_print_nothing_until_written(found):
    names = titles(sequence.story(found))
    for title in ('About Vantage Risk Solutions', 'Your team', 'How we work together through the year'):
        assert title not in names
    full = written(found, team=3, bios=True)
    names = titles(sequence.story(full))
    for title in (
        'About Vantage Risk Solutions',
        'Your team',
        'How we work together through the year',
        'Your plan experience',
        'Next steps',
        'Person 0',
    ):
        assert title in names


def test_J125_the_team_prints_eight_cards_a_page(found):
    names = titles(sequence.story(written(found, team=9)))
    assert names.count('Your team') == 2


def test_J42_pages_switched_off_do_not_print(found):
    full = written(found, team=2, bios=True)
    for page in ('about', 'team', 'experience', 'calendar', 'bios'):
        full['pages'][page] = False
    names = titles(sequence.story(full))
    for title in (
        'About Vantage Risk Solutions',
        'Your team',
        'Your plan experience',
        'How we work together through the year',
        'Person 0',
    ):
        assert title not in names
    assert '[Thank you]' in names  # never hidden


def test_J131_J133_GD1_one_table_per_plan_set_by_the_pages_the_builder_shows(found):
    names = titles(sequence.story(found))
    for line in found['lines']:
        for page in line['pages']:
            if page['part'] == 'options' and page['caption']:
                assert f'{line["label"]} — {page["caption"]}' in names


def test_J132_your_options_prints_when_a_line_runs_over_several_pages(found):
    names = titles(sequence.story(found))
    for line in found['lines']:
        several = len([page for page in line['pages'] if page['part'] == 'options']) > 1
        assert (f'{line["label"]} — your options' in names) == several


def test_J134_the_cost_only_line_when_the_comparison_part_is_off(found):
    off = copy.deepcopy(found)
    dental = next(line for line in off['lines'] if line['key'] == 'dental')
    dental['parts']['comparison'] = False
    names = titles(sequence.story(off))
    assert 'Dental — Delta Dental' in names  # its cost table, under the page's caption
    assert any(name.startswith('Dental — our recommendation') for name in names)
    pages = build.lay_out(off)
    page = next(p for p in pages if p['title'] == 'Dental — Delta Dental')
    table = next(item for item in page['frames'] if item['t'] == 'table')
    labels = {items.plain(cell['text']) for cell in table['cells'] if cell['col'] == 0}
    assert 'Est. group monthly premium' in labels and 'Annual Maximum' not in labels


def test_J135_what_employees_pay_only_when_an_option_has_an_employee_cost(found):
    assert not any('what employees pay' in name for name in titles(sequence.story(found)))
    paid = copy.deepcopy(found)
    dental = next(line for line in paid['lines'] if line['key'] == 'dental')
    for plan in dental['plans'].values():
        plan['employee'] = {'EE': 12.5, 'ES': 40.0, 'EC': 35.0, 'FAM': 60.0}
    assert 'Dental — what employees pay' in titles(sequence.story(paid))


def test_J136_J165_one_panel_for_one_pick_one_table_when_several_answer(found):
    dental = next(line for line in found['lines'] if line['key'] == 'dental')
    assert len(recommend.answers(dental)) == 1
    page = recommend.pages(dental, _colours())[0]
    panel = next(f for f in page if isinstance(f, tb.Table))  # the WE RECOMMEND panel: one table, as the old one was
    assert panel.rows[0]['cells'][0]['rowspan'] == len(panel.rows)  # the plan down its first column
    assert panel.rows[0]['cells'][0]['paras'][0]['runs'][0]['text'] == 'WE RECOMMEND'
    medical = next(line for line in found['lines'] if line['key'] == 'medical')
    pairs = recommend.answers(medical)
    currents = [current['id'] for _plan, current in pairs]
    assert len(pairs) > len(set(currents))  # two plans answer one current plan (J165)
    assert any(f.__class__.__name__ == 'Table' for f in recommend.several(pairs, medical, _colours(), ''))


def test_J136_GD1_the_reasons_sit_20_points_under_the_panel_as_the_old_page_put_them(found):
    page = next(p for p in build.lay_out(found) if p['title'] == 'Dental — our recommendation')
    panel = next(item for item in page['frames'] if item['t'] == 'table')
    why = next(item for item in page['frames'] if item['t'] == 'text' and items.plain(item).startswith('Why'))
    assert why['y'] == pytest.approx(panel['y'] + panel['h'] + 12 + 8)  # a 12 pt gap, then the rationale's own 8


def _colours():
    return furniture.palette(None)


def test_J126_J165_the_overview_prints_each_answer_and_no_total_when_one_plan_has_two(found):
    rows = glance.rows(found['glance_facts'])
    medical = [row for row in rows if row['line'] == 'medical']
    assert len(medical) == 4 and all(row['replacing'] for row in medical)
    assert glance.total(found['glance_facts']) is None  # two picks for one current plan: no honest total


def test_J137_nothing_to_compare_still_says_a_sentence(found):
    empty = copy.deepcopy(found)
    empty['lines'] = []
    pages = build.lay_out(empty)
    page = next(p for p in pages if p['title'] == 'Your coverage')
    text = ' '.join(items.plain(item) for item in page['frames'] if item['t'] == 'text')
    assert 'Your plan options will follow from your Vantage Risk Solutions benefits advisor.' in text


def test_J140_GD1_no_type_under_the_floor_and_no_frame_past_the_body(found):
    pages = build.lay_out(found)
    for page in pages:
        if page['kind'] == 'full':
            continue
        for item in page['frames']:
            bottom = max(item['y1'], item['y2']) if item['t'] == 'line' else item['y'] + item['h']
            assert bottom <= tokens.BODY_TOP + tokens.BODY_H + 0.01, page['title']
            if item['t'] == 'table':
                sizes = [
                    seg['size']
                    for c in item['cells']
                    for p in c['text']['paragraphs']
                    for ln in p['lines']
                    for seg in ln
                ]
                assert min(sizes) >= tokens.TABLE_TYPE['floor'], page['title']
        fit = page['fit']
        if fit:
            assert fit['size'] >= fit['floor'] == tokens.TABLE_TYPE['floor']
