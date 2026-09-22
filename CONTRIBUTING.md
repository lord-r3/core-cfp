# Contributing a deadline

Found a conference on the site with a wrong, missing, or outdated deadline? Please open a
pull request rather than an issue — it's usually a single small file.

1. Find the conference's CORE ranking id in [`data/core_rankings.csv`](data/core_rankings.csv)
   (first column) if its acronym is ambiguous — the build will warn you if it is.
2. Copy [`data/overrides/_example.yml`](data/overrides/_example.yml) to
   `data/overrides/<acronym>.yml` (lowercase, e.g. `data/overrides/icse.yml`).
3. Fill in the real deadline, straight from the conference's own CFP page — not from a
   secondary aggregator:

   ```yaml
   acronym: ICSE
   year: 2027
   deadline: "2026-08-15"     # ISO date, or a full timestamp
   timezone: "AoE"            # AoE (Anywhere on Earth), UTC, CEST, ...
   cfp_url: "https://conf.researchr.org/track/icse-2027/..."
   notes: "Optional: abstract deadline, rebuttal period, etc."
   verified_by: "your-github-username"
   ```

4. Open a pull request. Once merged, it's live within a few minutes (the deploy workflow
   rebuilds automatically) and takes precedence over any auto-detected guess for that
   conference.

You can also add `place`, `publisher`, and `open_access` (see the commented-out fields
in `_example.yml`) independently of the deadline fields above - e.g. to add a publisher
without knowing the current CFP deadline.

## Ambiguous acronyms

A handful of acronyms are shared by more than one CORE-ranked conference in different
fields (e.g. `IE`, `SAC`). If `data/overrides/<acronym>.yml` matches more than one entry,
the build log will print a warning and skip the override — add an explicit `id:` field
(the CORE id from `data/core_rankings.csv`) to disambiguate:

```yaml
id: 1629
acronym: AAAI
...
```

## Adding a conference that's missing entirely

Only CORE A*/A/B-ranked conferences are listed (see the README). If a conference is
missing despite being ranked A*/A/B in the current CORE round, it likely means
`data/core_rankings.csv` is stale — re-run `python scripts/fetch_core_rankings.py`
and commit the update in your PR instead of adding it as an override.
