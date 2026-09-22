#!/usr/bin/env python3
"""Merge the CORE ranking export with community overrides and imported
community deadlines into site/data/conferences.json, which the static
frontend reads.

Precedence per conference: a verified override (data/overrides/*.yml) always
wins; otherwise a community-sourced deadline (data/external_cache.json) is
used and clearly flagged as such; otherwise no deadline is known.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_core_rows, normalize_acronym  # noqa: E402

OVERRIDES_DIR = ROOT / "data" / "overrides"
EXTERNAL_CACHE = ROOT / "data" / "external_cache.json"
OUTPUT_JSON = ROOT / "site" / "data" / "conferences.json"


def load_overrides():
    overrides = []
    if not OVERRIDES_DIR.exists():
        return overrides
    for path in sorted(OVERRIDES_DIR.glob("*.y*ml")):
        if path.name.startswith("_"):
            continue  # e.g. _example.yml, not a real override
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        data["_file"] = path.name
        overrides.append(data)
    return overrides


def load_external_cache():
    if not EXTERNAL_CACHE.exists():
        return {}
    return json.loads(EXTERNAL_CACHE.read_text(encoding="utf-8"))


def index_overrides(overrides, rows):
    """Return (by_id, by_acronym) lookups. Acronym-keyed overrides are only
    honoured when the acronym is unique among the included conferences."""
    acronym_counts = {}
    for row in rows:
        key = normalize_acronym(row["acronym"])
        acronym_counts[key] = acronym_counts.get(key, 0) + 1

    by_id, by_acronym = {}, {}
    for o in overrides:
        core_id = o.get("id")
        acronym = normalize_acronym(o.get("acronym") or "")
        if core_id is not None:
            by_id[int(core_id)] = o
        elif acronym and acronym_counts.get(acronym) == 1:
            by_acronym[acronym] = o
        elif acronym:
            print(
                f"WARNING: override {o.get('_file')} uses ambiguous acronym "
                f"'{acronym}' (matches {acronym_counts.get(acronym, 0)} conferences) "
                "- add an explicit `id:` field to disambiguate. Skipping."
            )
    return by_id, by_acronym


def merge(rows, by_id, by_acronym, external_cache):
    out = []
    for row in rows:
        override = by_id.get(row["id"]) or by_acronym.get(normalize_acronym(row["acronym"]))
        external = external_cache.get(str(row["id"]))

        entry = dict(row)
        if override and override.get("deadline"):
            entry.update(
                deadline=override.get("deadline"),
                timezone=override.get("timezone", "AoE"),
                cfp_url=override.get("cfp_url"),
                event_date=None,
                place=None,
                year=override.get("year"),
                notes=override.get("notes"),
                status="verified",
                source=None,
                source_url=None,
                updated_by=override.get("verified_by"),
                checked_at=None,
            )
        elif external and external.get("deadline"):
            entry.update(
                deadline=external.get("deadline"),
                timezone=external.get("timezone"),
                cfp_url=external.get("cfp_url"),
                event_date=external.get("event_date"),
                place=external.get("place"),
                year=None,
                notes=None,
                status="community",
                source=external.get("source"),
                source_url=external.get("source_url"),
                updated_by=None,
                checked_at=external.get("checked_at"),
            )
        else:
            entry.update(
                deadline=None,
                timezone=None,
                cfp_url=None,
                event_date=None,
                place=None,
                year=None,
                notes=None,
                status="unknown",
                source=None,
                source_url=None,
                updated_by=None,
                checked_at=None,
            )
        out.append(entry)

    out.sort(key=lambda e: (e["deadline"] is None, e["deadline"] or "", e["acronym"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(out),
        "conferences": out,
    }


def main():
    rows = load_core_rows()
    overrides = load_overrides()
    external_cache = load_external_cache()
    by_id, by_acronym = index_overrides(overrides, rows)
    database = merge(rows, by_id, by_acronym, external_cache)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(database, indent=2, ensure_ascii=False), encoding="utf-8")

    counts = {"verified": 0, "community": 0, "unknown": 0}
    for e in database["conferences"]:
        counts[e["status"]] += 1
    print(
        f"Wrote {database['count']} conferences to {OUTPUT_JSON} "
        f"({counts['verified']} verified, {counts['community']} community-sourced, "
        f"{counts['unknown']} without a known deadline)"
    )


if __name__ == "__main__":
    main()
