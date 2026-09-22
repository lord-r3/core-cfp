#!/usr/bin/env python3
"""Import historical acceptance-rate data from emeryberger/csconferences and match
it against our CORE-ranked conference list.

That project is a single, actively-maintained flat CSV of
Area,Conference,Year,Sequence,Accepted,Submitted,Source,Notes - exactly the
acronym+year+counts shape we need, so no HTML scraping is required (unlike
scripts/import_external.py's deadline sources, which are either a tarball of YAML
files or single YAML files).

Writes data/acceptance_rates.json, consumed by build_database.py. This is supplementary
info, not part of the deadline-verification tiers - a conference can have an acceptance
rate regardless of whether its deadline is verified, community-sourced, or unknown.
"""
import csv
import io
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_core_rows, normalize_acronym  # noqa: E402

OUTPUT_PATH = ROOT / "data" / "acceptance_rates.json"
USER_AGENT = "corecfp-bot/0.1 (+https://github.com/; importing public conference acceptance-rate data)"
CSCONFERENCES_CSV = "https://raw.githubusercontent.com/emeryberger/csconferences/master/csconferences.csv"
YEARS_KEPT = 6


def fetch_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def build_core_index():
    index = {}
    for row in load_core_rows():
        index.setdefault(normalize_acronym(row["acronym"]), []).append(row)
    return index


def main():
    core_index = build_core_index()
    raw = fetch_url(CSCONFERENCES_CSV).decode("utf-8")

    by_acronym = {}
    for row in csv.DictReader(io.StringIO(raw)):
        try:
            accepted, submitted, year = int(row["Accepted"]), int(row["Submitted"]), int(row["Year"])
        except (KeyError, ValueError):
            continue
        if submitted <= 0:
            continue
        key = normalize_acronym(row["Conference"])
        by_acronym.setdefault(key, []).append(
            {"year": year, "accepted": accepted, "submitted": submitted}
        )

    results = {}
    matched = 0
    for key, entries in by_acronym.items():
        candidates = core_index.get(key)
        if not candidates or len(candidates) > 1:
            continue  # skip unmatched/ambiguous, same rule as everywhere else
        entries.sort(key=lambda e: e["year"], reverse=True)
        for e in entries[:YEARS_KEPT]:
            e["rate"] = round(e["accepted"] / e["submitted"] * 100, 1)
        results[str(candidates[0]["id"])] = entries[:YEARS_KEPT]
        matched += 1

    OUTPUT_PATH.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Matched {matched} conferences; wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
