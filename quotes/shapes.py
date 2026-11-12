"""The plain facts every pure rule of the Advisor reads (plan.md §5.4, §5.5): a plan and its line.

Selectors build `PlanData` from model rows (`selectors.state`); the pure modules (`math/`, `packages`, `presented`,
`order`, `slots`, `closeness`, `facts`) read nothing else, so they run without a database.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PlanData:
    id: int
    role: str
    carrier: str = ''
    name: str = ''
    plan_number: str = ''
    values: dict = field(default_factory=dict)
    enrollment: dict = field(default_factory=dict)  # its own typed counts (§5.5 step 1), under the line's switch
    census_names: tuple = ()  # a current plan's census plan texts matched by hand (step 4; F90)
    renews: int | None = None
    replaces: tuple = ()
    recommended: bool = False
    sold: bool = False
    starred: bool = False
    sort_order: int = 0
    # The plan this one is a priced version of (it rides right behind it; F120, slice 35); None for every other plan,
    # copies included (a copy is a standalone peer, D-049).
    version_of: int | None = None
    # A premium holiday's credit, {annual} or {months} (F80); None for every other plan.
    credit: dict | None = None

    @property
    def label(self):
        return self.name or self.carrier or f'Plan {self.id}'

    @property
    def words(self):
        """How a sentence names the plan: "Aetna HMO 1500"."""
        return f'{self.carrier} {self.name}'.strip() or f'Plan {self.id}'


@dataclass
class People:
    """What a line knows of its people beyond its plans' own typed counts (§5.5; F88, F91): the figure typed for the
    whole line and the line's one switch, when its typed counts were saved, the census's figures for the line
    (`census.rollup.for_line`) and when the census was last imported, and — for the lines that borrow them —
    medical's people as `(figures, source)` (worksite tier-rated lines, OQ19; stop-loss lives, F98)."""

    on: bool = True
    figure: dict = field(default_factory=dict)
    typed_at: datetime | None = None
    census: dict | None = None
    imported_at: datetime | None = None
    medical: tuple | None = None

    @property
    def stale(self):
        """Counts typed before the latest census import give way to the census (F91)."""
        if self.imported_at is None:
            return False
        return self.typed_at is None or self.typed_at < self.imported_at


@dataclass
class LineData:
    rate_basis: str
    plans: list
    key: str = ''
    people: People = field(default_factory=People)

    def __post_init__(self):
        self.by_id = {plan.id: plan for plan in self.plans}
        self.current = sorted((p for p in self.plans if p.role == 'current'), key=lambda p: (p.sort_order, p.id))

    def base_ids(self, plan):
        """The current plan(s) a plan is measured against, its comparison base (§5.5): a renewal → its current plan;
        an alternate with `replaces` → the plans it replaces; an alternate without them on a line with exactly one
        current plan → that plan; otherwise none. In the current plans' slot order."""
        slot = {p.id: i for i, p in enumerate(self.current)}
        if plan.role == 'renewal':
            ids = [plan.renews] if plan.renews in slot else []
        elif plan.role == 'alternate' and plan.replaces:
            ids = [pid for pid in plan.replaces if pid in slot]
        elif plan.role == 'alternate' and len(self.current) == 1:
            ids = [self.current[0].id]
        else:
            ids = []
        return sorted(ids, key=slot.get)

    def root(self, plan):
        """The quote a priced version was made from (followed to the carrier's own quote); the plan itself otherwise."""
        seen = set()
        while plan.version_of in self.by_id and plan.id not in seen:
            seen.add(plan.id)
            plan = self.by_id[plan.version_of]
        return plan
