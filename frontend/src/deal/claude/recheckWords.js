// The re-check card's words and groups (plan.md §10.4, §10.7; D93, E77; slice 22; the old ProposedChangesCard's flag
// re-check, D-119). Pure: a re-check's change set in, what the card shows out.

export const CONFIDENCE_WORD = {
  low: "unsure",
  medium: "fairly sure",
  high: "",
};

/** The ids ticked when the card opens: what Claude proposes (an unsure fix arrives unticked). */
export function firstPicks(changeSet) {
  return new Set(
    (changeSet?.items || []).filter((item) => item.tick).map((item) => item.id),
  );
}

function byPlan(items) {
  const groups = [];
  const found = new Map();
  items.forEach((item) => {
    if (!found.has(item.plan)) {
      const group = {
        plan: item.plan,
        label: `${item.carrier} ${item.name}`,
        items: [],
      };
      found.set(item.plan, group);
      groups.push(group);
    }
    found.get(item.plan).items.push(item);
  });
  return groups;
}

/** The card's two sections: what Claude agrees with (approve) and what it would fix, each by plan. */
export function sections(changeSet) {
  const items = changeSet?.items || [];
  const agree = items.filter((item) => item.op === "confirm");
  const fix = items.filter((item) => item.op !== "confirm");
  return [
    agree.length && {
      key: "approve",
      groups: byPlan(agree),
      title: `Claude agrees — approve ${agree.length === 1 ? "this" : `these ${agree.length}`}`,
      note: "Re-read against the page and right as read: applying approves them and the warning clears.",
    },
    fix.length && {
      key: "fix",
      groups: byPlan(fix),
      title: `Claude proposes ${fix.length === 1 ? "a fix" : `${fix.length} fixes`}`,
      note: "The page says something else: applying writes the value the page prints.",
    },
  ].filter(Boolean);
}

/** "Claude re-checked the flags: 3 look right, 1 needs a fix". */
export function recheckTitle(changeSet) {
  const counts = changeSet?.counts || {};
  const fixes = counts.fixes || 0;
  return `Claude re-checked the flags: ${counts.approvals || 0} look right, ${fixes} need${fixes === 1 ? "s" : ""} a fix`;
}

/** "Re-read 5 flagged values against their pages in “Cigna SBC”." */
export function recheckSource(changeSet, nameOf) {
  const counts = changeSet?.counts || {};
  const total =
    (counts.approvals || 0) + (counts.fixes || 0) + (counts.unverified || 0);
  const documents = changeSet?.documents || [];
  const name = documents.length === 1 ? nameOf(documents[0]) : "";
  const values = `${total} flagged value${total === 1 ? "" : "s"}`;
  return `Re-read ${values} against their pages${name ? ` in “${name}”` : ""}`;
}

/** The note under a row: its page and how sure Claude was. */
export function rowMeta(value) {
  return [
    value.page ? `p.${value.page}` : "",
    CONFIDENCE_WORD[value.confidence] || "",
    value.note || "",
  ]
    .filter(Boolean)
    .join(" · ");
}
