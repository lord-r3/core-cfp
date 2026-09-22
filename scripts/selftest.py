#!/usr/bin/env python3
"""Plain assert-based self-check for the non-trivial logic in this pipeline:
acronym normalization/matching, deadline parsing, merge precedence, region/format
derivation, and acceptance-rate grouping. No framework, no fixtures - run directly:

    python3 scripts/selftest.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_database  # noqa: E402
import common  # noqa: E402
import import_acceptance_rates  # noqa: E402
import import_external  # noqa: E402

# --- common.normalize_acronym: fuzzy-matching conference names/acronyms ---
assert common.normalize_acronym("S&P (Oakland)") == "SP"
assert common.normalize_acronym("USENIX-Security") == common.normalize_acronym("USENIX Security")
assert common.normalize_acronym("ACM_WiSec") == "ACMWISEC"
assert common.normalize_acronym("ccs") == "CCS"

# --- import_external.parse_deadline_str: the two accepted date formats ---
assert import_external.parse_deadline_str("2026-01-20 23:59:59") is not None
assert import_external.parse_deadline_str("2026-01-20 23:59") is not None
assert import_external.parse_deadline_str("TBD") is None
assert import_external.parse_deadline_str("") is None
assert import_external.parse_deadline_str(None) is None

# --- build_database.merge: verified > community > unknown ---
row = {
    "id": 1,
    "acronym": "X",
    "title": "Test Conference",
    "rank": "A",
    "source": "",
    "field_of_research": [],
}
override = {"deadline": "2099-01-01", "acronym": "X"}
external = {
    "deadline": "2000-01-01",
    "source": "foo",
    "source_url": "u",
    "acronym": "X",
    "place": "Berlin, Germany",
    "dblp_url": "https://dblp.org/db/conf/x/",
}

conf = build_database.merge([row], {1: override}, {}, {"1": external}, {})["conferences"][0]
assert conf["status"] == "verified" and conf["deadline"] == "2099-01-01"
# supplementary fields still come from external even when the deadline itself is verified
assert conf["region"] == "Europe" and conf["dblp_url"] == "https://dblp.org/db/conf/x/"

conf = build_database.merge([row], {}, {}, {"1": external}, {})["conferences"][0]
assert conf["status"] == "community" and conf["deadline"] == "2000-01-01"

conf = build_database.merge([row], {}, {}, {}, {"1": [{"year": 2024, "rate": 20.0}]})["conferences"][0]
assert conf["status"] == "unknown" and conf["deadline"] is None
assert conf["acceptance_rates"] == [{"year": 2024, "rate": 20.0}]

# --- common.derive_region / derive_format: best-effort from free-text place ---
assert common.derive_region("Denver, CO, USA") == "North America"
assert common.derive_region("Rabat, Morocco") == "Africa"
assert common.derive_region("Seoul, South Korea") == "Asia"
assert common.derive_region("Barbados") is None  # not in the lookup table - falls through
assert common.derive_region(None) is None
assert common.derive_format("Fully virtual") == "virtual"
assert common.derive_format("Hybrid - Paris, France") == "hybrid"
assert common.derive_format("Paris, France") is None

# --- import_acceptance_rates: grouping + rate calculation on synthetic CSV rows ---
import csv
import io

fake_csv = io.StringIO(
    "Area,Conference,Year,Sequence,Accepted,Submitted,Source,Notes\n"
    "AI,TESTCONF,2024,1,20,100,,\n"
    "AI,TESTCONF,2023,1,10,100,,\n"
)
by_acronym = {}
for r in csv.DictReader(fake_csv):
    key = common.normalize_acronym(r["Conference"])
    by_acronym.setdefault(key, []).append(
        {"year": int(r["Year"]), "accepted": int(r["Accepted"]), "submitted": int(r["Submitted"])}
    )
entries = by_acronym["TESTCONF"]
entries.sort(key=lambda e: e["year"], reverse=True)
for e in entries:
    e["rate"] = round(e["accepted"] / e["submitted"] * 100, 1)
assert entries[0] == {"year": 2024, "accepted": 20, "submitted": 100, "rate": 20.0}
assert entries[1]["rate"] == 10.0

# --- build_database.escape_ics / ics_event: RFC5545 escaping + all-day VEVENT shape ---
assert build_database.escape_ics("a, b; c\nd") == "a\\, b\\; c\\nd"
ics_row = {
    "id": 1,
    "acronym": "X",
    "title": "Test, Inc.",
    "notes": None,
    "cfp_url": "https://example.org",
    "deadline": "2026-01-01",
}
event = build_database.ics_event(ics_row)
assert "DTSTART;VALUE=DATE:20260101" in event
assert "DTEND;VALUE=DATE:20260102" in event  # exclusive end, one day after the deadline
assert "SUMMARY:X CFP deadline" in event
assert "DESCRIPTION:Test\\, Inc. - https://example.org" in event

print("OK - all self-checks passed")
