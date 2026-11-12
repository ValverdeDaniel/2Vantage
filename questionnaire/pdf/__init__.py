"""The questionnaire's PDFs (plan.md §9.12; G56–G63, G135): the carrier's own form, filled.

- `printed`: what a form prints — stored and approved answers only (a client's waiting answer never prints, OQ85),
  hidden answers dropped (G19), the first filled rows first (B1), and the signatures;
- `display`: how one answer reads in a carrier's box;
- `stamp_place` (pure) and `stamp_draw`: Florida Blue's flat blank with the answers stamped into its boxes (G57);
- `acroform`: Warner's and the SIIA disclosure's own fillable fields (G59);
- `attachment`: the page after the form for what its boxes cannot hold;
- `build`: one dispatch, the file name and the blank (G61, G62).
Ported from old Vantage 891f1b3 (`benefits/questionnaires/questionnaire_stamp.py`, `questionnaire_acroform.py`, the
attachment helpers of `questionnaire_pdf.py`; the replica itself is dropped, G60).
"""
