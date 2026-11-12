"""Filling a carrier's own workbook by patching its worksheet XML, and nothing else (plan.md §9.8; K90, K91, K96).

Ported unchanged from old Vantage 891f1b3 `benefits/pipeline/xlsx_fill.py` (the 2026-09-17 fidelity pass: a carrier
must not be able to tell our file from one a careful person filled in Excel), split by responsibility:
- `refs`: cell references and the error a mis-shaped template raises;
- `sheet`: one worksheet's XML, patched in place (a cell keeps its own style, the style decides the type, a formula is
  never overwritten, clearing never creates, strings are inline);
- `formulas`: does a formula on a patched sheet read a column we wrote (the recalculation flag);
- `package`: the zip, rewritten part by part the way Excel writes it (`fill`, `read_sheet`);
- `as_csv`: a filled sheet as Excel's "Save As → CSV UTF-8" renders it.
Dependency-free apart from openpyxl in `as_csv`, and knows nothing about benefits: bytes and a map of cells in, bytes
out. Openpyxl never saves a carrier file (a load/save drops logos, checkboxes and caption boxes).
"""
