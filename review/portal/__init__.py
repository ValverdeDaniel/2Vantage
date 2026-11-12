"""The client portal (plan.md §7.14, §8.20; Part L, L76–L110 and L136; slice 54, V2: intake, census and documents).

`guard` lets a link in (404, 410, 428, 403); `asked` is what a link asks now, the one allowlist; `payload` and its
parts (`intake_part`, `census_part`, `files_part`) build the page; `views` and `urls` are the public API; `throttles`
keep its rates per link; `words` the words its payload carries. Writes go through `review.services` (`answers`,
`client_adds`, `stamps`), which write through the owners' own doors.
"""
