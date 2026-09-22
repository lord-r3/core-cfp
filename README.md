# CORE CFP Deadlines

A [sec-deadlines](https://sec-deadlines.github.io/)-style static site listing submission
deadlines for [CORE](https://www.core.edu.au/)-ranked (A*/A/B) computer science conferences.

**Live idea, not a live API.** There is no official, machine-readable source of CFP
deadlines anywhere — CORE only publishes rankings, not deadlines. This project combines
three layers, each one only filling gaps the previous layer left (see `merge()` in
[`scripts/build_database.py`](scripts/build_database.py)):

1. **CORE rankings** ([`data/core_rankings.csv`](data/core_rankings.csv)) — the official
   ranking export, downloaded from [portal.core.edu.au](https://portal.core.edu.au/conf-ranks/).
   Refreshed occasionally by [`scripts/fetch_core_rankings.py`](scripts/fetch_core_rankings.py)
   (CORE only re-ranks every few years). This is the master list of *which* conferences
   are on the site at all - it never carries a deadline.
2. **"verified" — our own overrides** ([`data/overrides/`](data/overrides/)) — one YAML
   file per conference, added via pull request by someone who checked the real CFP page.
   Always wins. See [CONTRIBUTING.md](CONTRIBUTING.md).
3. **"community" — imported from other maintained deadline trackers**
   ([`data/external_cache.json`](data/external_cache.json), produced by
   [`scripts/import_external.py`](scripts/import_external.py)) — these projects are
   actively kept up to date by their own communities via their own pull requests, so
   their data is far more reliable than anything we could guess ourselves:
   - [ccfddl/ccf-deadlines](https://github.com/ccfddl/ccf-deadlines) (powers
     [ccfddl.com](https://ccfddl.com/) / aideadlines.org) — ~360 conferences, and
     conveniently ships its own CORE rank per conference, which we use to disambiguate.
   - [sec-deadlines](https://github.com/sec-deadlines/sec-deadlines.github.io),
     [se-deadlines](https://github.com/se-deadlines/se-deadlines.github.io),
     [hci-deadlines](https://github.com/hci-deadlines/hci-deadlines.github.io),
     [ds-deadlines](https://github.com/ds-deadlines/ds-deadlines.github.io) and
     [paperswithcode/ai-deadlines](https://github.com/paperswithcode/ai-deadlines) —
     forks of the same original Jekyll template, one per research area.

   Matching is by normalized acronym against the CORE list; ambiguous or unmatched
   entries are skipped rather than guessed at (see `import_external.py` for the exact
   logic). Still shown as "community-sourced", not "verified" - nobody in *this*
   project checked it against the primary CFP page.

[`scripts/build_database.py`](scripts/build_database.py) merges both into
`site/data/conferences.json`, which the plain HTML/CSS/JS frontend in [`site/`](site/) reads
client-side. There is no backend and no build step beyond that script.

Know another well-maintained "X-deadlines" style tracker that covers CORE-ranked
conferences? Add it to `CONFERENCE_DEADLINES_FAMILY` in `scripts/import_external.py` (or
open an issue) - most forks of the same template are a two-line addition.

## Scope

Only conferences ranked **A\***, **A**, or **B** in the current CORE ranking round are
included (~420 of the ~1000 entries in the full CORE list) — C-ranked and unranked entries,
and non-CS national/regional rankings, are left out to keep the list curatable. Change
`INCLUDED_RANKS` in [`scripts/common.py`](scripts/common.py) if you want a different cut.




## Disclaimer

This is an independent community project, not an official CORE resource. Rankings are
CORE's; deadlines are either verified directly against the primary CFP page or imported
from other community deadline trackers, clearly labelled as such on the site.
