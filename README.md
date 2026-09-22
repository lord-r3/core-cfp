# CORE CFP Deadlines

CORE CFP is an idea I wanted to implement for quite some time. I often times ask myself to which conference should I submit work on XY to. Then I check core, then I manually check CFP availabiltiy etc, looking for various conferences on various platforms, using Google, dark arts and what not to get to the next deadline that fits the strength of my contribution in a specific Field of Research.

While I love to use [sec-deadlines](https://sec-deadlines.github.io/) and others, I always missed a direct integration of [CORE](https://www.core.edu.au/)-ranked (A*/A/B) computer science conferences directly into the CfP overview.

**Live idea, not a live API.** There is no official, machine-readable source of CFP
deadlines anywhere — CORE only publishes rankings, not deadlines. This project combines
three layers, each one only filling gaps the previous layer left (see `merge()` in
[`scripts/build_database.py`](scripts/build_database.py)):

1. **CORE rankings** ([`data/core_rankings.csv`](data/core_rankings.csv)) — the official
   CORE export, downloaded from [portal.core.edu.au](https://portal.core.edu.au/conf-ranks/).
   Refreshed occasionally by [`scripts/fetch_core_rankings.py`](scripts/fetch_core_rankings.py)
   (CORE only re-ranks every few years).
2. **"verified" — our own overrides** ([`data/overrides/`](data/overrides/)) — one YAML
   file per conference, added via pull request by someone who checked the real CFP page. See [CONTRIBUTING.md](CONTRIBUTING.md).
3. **"community" — imported from other maintained deadline trackers**
   ([`data/external_cache.json`](data/external_cache.json), produced by
   [`scripts/import_external.py`](scripts/import_external.py)): These projects are
   actively kept up to date by their own communities via their own pull requests, so
   their data is typically reliable:
   - [ccfddl/ccf-deadlines](https://github.com/ccfddl/ccf-deadlines) (~360 conferences, and
     conveniently ships its own CORE rank per conference, which we use to disambiguate conferences with the same acronym.
   - [sec-deadlines](https://github.com/sec-deadlines/sec-deadlines.github.io),
     [se-deadlines](https://github.com/se-deadlines/se-deadlines.github.io),
     [usec-deadlines](https://github.com/usec-deadlines/usec-deadlines.github.io),
     [hci-deadlines](https://github.com/hci-deadlines/hci-deadlines.github.io),
     [ds-deadlines](https://github.com/ds-deadlines/ds-deadlines.github.io),
     [paperswithcode/ai-deadlines](https://github.com/paperswithcode/ai-deadlines),
     [yeah-tiger](https://github.com/yeah-tiger/yeah-tiger.github.io) (PL conferences) and
     [hcorinna/fair-deadlines](https://github.com/hcorinna/fair-deadlines) —
     forks of the same original Jekyll template, one per research area. fair-deadlines
     also lists journal special issues alongside conferences; only entries tagged
     `cat: conference` are imported.

   Matching is by normalized acronym against the CORE list: ambiguous or unmatched
   entries are skipped rather than guessed at (see `import_external.py` for the exact
   logic). Shown as "community-sourced", not "verified" - nobody in *this*
   project checked correctness against the primary CFP page.

[`scripts/build_database.py`](scripts/build_database.py) merges both into
`site/data/conferences.json`, which the plain HTML/CSS/JS frontend in [`site/`](site/) reads
client-side.

Know another well-maintained "X-deadlines" style tracker that covers CORE-ranked
conferences? Add it to `CONFERENCE_DEADLINES_FAMILY` in `scripts/import_external.py` (or
open an issue).

On top of the deadline itself, each conference also carries supplementary data that's
looked up independently of the deadline tiers above (a conference can have this even
without a known deadline):

- **Historical acceptance rates** ([`data/acceptance_rates.json`](data/acceptance_rates.json),
  via [`scripts/import_acceptance_rates.py`](scripts/import_acceptance_rates.py)) — imported
  from [emeryberger/csconferences](https://github.com/emeryberger/csconferences), a plain,
  actively-maintained CSV of accepted/submitted counts per year.
- **DBLP link** — captured from the `dblp` field already present in the ccf-deadlines /
  sec-deadlines-family data. We link to DBLP's own venue page rather than asserting a
  publisher or open-access status ourselves; those are optional manual override fields
  instead (see CONTRIBUTING.md).
- **Region / format (virtual or hybrid)** — best-effort, derived from the free-text
  `place` field (community-sourced, or manually added via an override) by
  `derive_region`/`derive_format` in `scripts/common.py`. Coverage is limited to
  conferences with a known `place`.

## Features

- Filter by rank, field of research, region, format, and free-text search; sort by
  nearest deadline, rank, or acronym.
- **Copy link to this view** — the current filter state lives in the URL, so a shared
  link reproduces the same filtered view for a co-author.
- **Export selection (.ics)** — download the currently filtered conferences (or a single
  one from its card) as calendar events.

## Scope

Only conferences ranked **A\***, **A**, or **B** in the current CORE ranking round are
included (~420 of the ~1000 entries in the full CORE list) — C-ranked and unranked entries,
and non-CS national/regional rankings, are left out to keep the list curatable. Change
`INCLUDED_RANKS` in [`scripts/common.py`](scripts/common.py) if you want a different cut.

## Disclaimer

This is an independent community project, not an official CORE resource. Rankings are
CORE's; deadlines are either verified directly against the primary CFP page or imported
from other community deadline trackers, clearly labelled as such on the site.
