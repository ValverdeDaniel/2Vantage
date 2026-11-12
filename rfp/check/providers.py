"""The export check's provider registry (plan.md §8.12; L120, K.6, O.1; slice 55): lines that apps to rfp's right add
to the deal's own problems, so the check never imports them (O.3.4: "rfp's export check … through providers that review
registers at apps.ready()").

`register(name, problems, stamp=None)`: `problems(deal) -> [problem]` (`problems.problem`'s shape, counts and words
only, never a value or a name); `stamp(deal) -> anything JSON` when what the lines read can move without the census
moving (a link submitted, an answer turning idle), so `checks_stamp` moves with it. Review registers the client's
census answers: not reviewed, still typing, going back. `problems(deal)` and `stamps(deal)` read every provider in
name order. Registered once per process; registering a name again replaces it.
"""

_providers = {}


def register(name, problems, stamp=None):
    _providers[name] = (problems, stamp)


def problems(deal):
    out = []
    for name in sorted(_providers):
        out += _providers[name][0](deal)
    return out


def stamps(deal):
    return {name: _providers[name][1](deal) for name in sorted(_providers) if _providers[name][1]}
