"""The questionnaire's reads (plan.md §6.8, §7.9; G.6): GETs write nothing (G26).

- `context`: one deal's facts, read once per request — the checklist choices, the one headcount, the forms resolved,
  the stored questionnaires, and (on demand) the prefill facts from `quotes.facts.group_facts` and the current plans;
- `payload`: the deal's forms (`GET deals/{id}/questionnaires/`) and one form (`GET …/{form}/`);
- `items`: `intake.providers.questionnaire_items`, the checklist's form rows (B22, B26; G11);
- `sources`: the answers with their sources, for the review marks (E103).
"""
