"""The client spreadsheet (plan.md §9.4; J145–J154; slice 27): `facts` reads the deal once through an allow-list,
`layout` names the tabs, `tabs/` draws each one on the pure sheet model (`model`, `cells`, `styles`, `formulas`,
`print_plan`), and `write` writes the model with XlsxWriter through `documents.xlsx_safe`. `build.workbook(deal)` is
the door the download (and, from slice 32, Issue) calls."""
