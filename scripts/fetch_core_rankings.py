#!/usr/bin/env python3
"""Refresh data/core_rankings.csv from the public CORE conference ranking portal.

The portal (portal.core.edu.au) has no official API, but its search page exposes
a CSV export at the URL below that returns the full result set regardless of the
`page` parameter. CORE only re-ranks conferences every few years, so this only
needs to be run occasionally (see .github/workflows/refresh-core.yml).

Raw CSV columns (no header row in the source): id, title, acronym, source,
rank, active, for_code_1, for_code_2, for_code_3
"""
import csv
import io
import sys
import urllib.request
from pathlib import Path

CORE_EXPORT_URL = (
    "https://portal.core.edu.au/conf-ranks/?search=&by=all&sort=arank&page=1&do=Export"
)
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "core_rankings.csv"
USER_AGENT = "corecfp-bot/0.1 (+https://github.com/; contact via repo issues)"


def fetch() -> str:
    request = urllib.request.Request(CORE_EXPORT_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def main() -> None:
    text = fetch()
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 100:
        sys.exit(
            f"CORE export only returned {len(rows)} rows, expected ~1000 - "
            "not overwriting the existing file. The portal's markup may have changed."
        )
    OUTPUT_PATH.write_text(text, encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
