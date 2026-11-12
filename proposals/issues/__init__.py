"""Issue to client (plan.md §7.12 "Issuing", §8.15; J96–J104, J.6.4; slice 32).

- `gate`: the sentences that refuse an issue (readiness, the 16-column cap, nothing on the proposal).
- `start`: Issue and Retry, transaction 1 under the Deal lock: the gate, quotes stamps the option numbers, the
  version is made `building` and the `issue` job is queued.
- `build`: the `issue` job (registered with ai in ProposalsConfig.ready): the three files built outside any lock.
- `finish`: transaction 2: the files stored as protected Documents, the version `issued`, the stage moved to
  Proposal; or the version `failed`, with its sentence.
- `selectors`: the issued list; `packet`: an issue's stored files in one zip; `catalog`: the vocabularies.
"""
