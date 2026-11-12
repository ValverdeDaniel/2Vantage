"""The generator of Florida Blue's carrier data (G124): a dev tool, never run by the app.

`parse.parse_template(xml_bytes)` reads the XFA template packet of the carrier's original PDF into plain data, and
`render.render_data_module(parsed)` writes it as `questionnaire/forms/fl_blue_51_data.py`. The command is
`manage.py extract_questionnaire_spec`. Ported from old Vantage 891f1b3 (`benefits/questionnaires/xfa_extract.py`).
"""
