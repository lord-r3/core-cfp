#!/usr/bin/env python3
"""Plain assert-based self-check for the non-trivial logic in this pipeline:
acronym normalization/matching, deadline parsing, and merge precedence. No
framework, no fixtures - run directly:

    python3 scripts/selftest.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_database  # noqa: E402
import common  # noqa: E402
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
external = {"deadline": "2000-01-01", "source": "foo", "source_url": "u", "acronym": "X"}

conf = build_database.merge([row], {1: override}, {}, {"1": external})["conferences"][0]
assert conf["status"] == "verified" and conf["deadline"] == "2099-01-01"

conf = build_database.merge([row], {}, {}, {"1": external})["conferences"][0]
assert conf["status"] == "community" and conf["deadline"] == "2000-01-01"

conf = build_database.merge([row], {}, {}, {})["conferences"][0]
assert conf["status"] == "unknown" and conf["deadline"] is None

print("OK - all self-checks passed")
