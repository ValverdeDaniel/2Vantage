"""The golden deals (plan.md §12.6, §13.4): seed only, last in the chain (§3.3).

Only `manage.py seed_golden` and the root `conftest.py` import this app. It holds one JSON spec per deal with its
parity profile (`specs/`, read by `specs.py`), the answer keys (`keys/`) and the seed (`seed.py`), which builds
every deal through the services of the apps to its left.
"""
