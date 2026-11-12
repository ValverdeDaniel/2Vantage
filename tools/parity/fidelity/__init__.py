"""The Fidelity lane (plan.md §12.7; Part Q, Q.2, Q.5): old Vantage's client files beside 2Vantage's, compared.

`fetch` runs on the host (stdlib only) and downloads both apps' files; the rest runs in the parity tools image
(openpyxl, pypdf, python-pptx, poppler) and compares them: `xlsx`, `pdf`, `pptx` each turn a pair of files into
differences, `mask` hides what may differ by design on both sides (dates, stamps, ids, authors), `intended` reads
`intended.yaml` and labels the differences it lists, and `report` writes report.md and differences.json.
"""
