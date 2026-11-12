"""The questionnaire engine (plan.md §6.8; G12–G25): pure functions over a form spec — no Django, no database.

- `spec`: navigating a spec (its scalar fields, blocks and fields by key);
- `conditions`: `visible_if` and block gates (G14, G15);
- `options`: the dependent pickers, aliases, effects and the SIC pair (G12, G13, G16);
- `walk`: what a form shows for its answers, in order: visible fields, slot order, drivers, visible values, progress
  and the blank required answers (G19, G20, G25);
- `narrow`: a form as a link asks it, and its gate questions (G22, G24).
The server is the one engine: the browser holds no cascade, progress or option logic (G25).
"""
