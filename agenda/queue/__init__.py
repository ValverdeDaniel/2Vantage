"""The Work queue and the home figures (plan.md §7.15, §8.3; I70–I87, I122–I127; A9–A12; slice 61).

- `rows`: pure: one deal's queue row, a hand task's and a nudge's, from the facts and steps the Agenda tab reads;
- `feed`: `GET work-queue/`, every live deal's row in a fixed number of queries (`agenda.facts.facts_for` inside one
  batch scope), the open tasks and nudges, the owners and the Prospects cards;
- `stats`: `GET work-queue/stats/`, actions completed this week and sales this month, each with its change and a real
  ten-point series (I83, I84, I127; OQ94).
Filters, sorts, the one-per-client collapse and Responses first run in the browser over the one payload (ch. 12).
"""
