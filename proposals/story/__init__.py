"""The client story: what the Presentation format prints, page by page (plan.md §9.5; J.6.3). `facts` (with
`line_facts` and `firm_read`) reads one client-shaped Facts; `sequence` orders the pages from the page modules
(`opening`, `firm`, `coverage`, `glance`, `answer`, `line_pages`, `exhibit`, `exhibit_rows`, `recommend`, `closing`),
each pure over the Facts and built through `look`; `build.deck` lays them out once (`layout.record`). `ledger` is the
builder's page ledger (slice 26)."""
