"""The renewal letter's blocks: the carrier's renewal and ours against it (J65; OQ38, default yes: the offer shows as
$/yr and % change). Old Vantage 891f1b3 `exec_summary._b_renewal_offer` and `_b_renewal_vs_recommended`. Pure.

They quote the letter's facts as a person typed them (`facts['renewal_offer']`: renewal_pct_change,
renewal_premium_annual, stated_current_premium_annual, group_number), never a quote guessed to be "the renewal". The
letter is a medical renewal letter, so the comparison reads the medical line. The two percentages ride different
censuses, so ours against theirs is reported in points, never as one combined dollar figure.
"""

from quotes import math as m

from . import reading as r
from . import words as w

MEDICAL = 'medical'
NO_LETTER = "No renewal letter's figures on this deal"
BASES_APART = 0.10  # the letter's stated premium and our rating of today differ by more than this: say so


def _offer(facts):
    offer = facts.get('renewal_offer')
    if not offer:
        raise r.Refused(NO_LETTER)
    return offer


def renewal_offer(facts, _key=None):
    """What the incumbent asked for, in their own figures; a flat renewal (0%) is a real answer."""
    offer = _offer(facts)
    pct, annual = offer.get('renewal_pct_change'), offer.get('renewal_premium_annual')
    if pct is None and annual is None:
        raise r.Refused('The renewal letter has no renewal figures')
    if pct is not None:
        sub = (
            f'{w.per_year(annual)} as offered in the renewal letter'
            if annual is not None
            else 'as offered in the renewal letter'
        )
        return {'value': pct, 'value_label': w.pct(pct), 'sub': sub, 'delta_dir': w.direction(pct)}
    return {'value': annual, 'value_label': w.per_year(annual), 'sub': 'as offered in the renewal letter'}


def renewal_vs_recommended(facts, _key=None):
    offer = _offer(facts)
    theirs = offer.get('renewal_pct_change')
    if theirs is None:
        raise r.Refused('The renewal letter has no stated % change to compare against')
    line = next((entry for entry in facts['lines'] if entry['key'] == MEDICAL), None)
    if line is None:
        raise r.Refused('This deal has no medical line to compare the renewal against')
    plan = r.pick(line)
    if not plan:
        raise r.Refused(r.NO_PICK)
    if plan['change'] is None:
        if r.several(line):
            raise r.Refused(r.SEVERAL_CURRENT)
        raise r.Refused(
            r.NO_ENROLLMENT if line['no_people'] else 'Needs a current plan and a recommendation with rates'
        )
    ours = plan['change']['pct']
    points = m.change(ours, theirs)['delta']
    shown = m.round_decimal(m.decimal(points), 1)
    if shown == 0:
        label = 'matches the renewal'
    else:
        label = f'{abs(shown):.1f} pts {"better" if shown < 0 else "worse"} than the renewal'
    sub = f'{w.pct(theirs)} offered · {w.pct(ours)} as recommended ({plan["words"]})'
    stated, base = offer.get('stated_current_premium_annual'), r.baseline(line, plan)
    if stated and base and base['annual']:
        apart = m.change(stated, base['annual'])
        if apart['pct'] is not None and abs(apart['pct']) > BASES_APART * 100:
            sub += f' — note: the letter states {w.per_year(stated)} current where we rate {w.per_year(base["annual"])}'
    return {'value': points, 'value_label': label, 'sub': sub, 'delta': points, 'delta_dir': w.direction(points)}
