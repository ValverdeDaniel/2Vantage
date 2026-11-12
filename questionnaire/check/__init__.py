"""The check before a questionnaire downloads (plan.md §9.12; G64–G66): `problems` (pure) and `report` (reads).

Count and warn: nothing here refuses a download. The report is shown before the door; the person downloads anyway or
fixes first. A download carrying `?ack=` that no longer matches the report answers 409 with the fresh one, so a
problem that appeared since the modal opened is never sent unseen.
"""
