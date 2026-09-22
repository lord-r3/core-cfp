#!/usr/bin/env python3
"""Merge the CORE ranking export with community overrides and imported
community data into site/data/conferences.json, which the static frontend reads.

Deadline precedence per conference: a verified override (data/overrides/*.yml) always
wins; otherwise a community-sourced deadline (data/external_cache.json) is used and
clearly flagged as such; otherwise no deadline is known. Everything else attached here
(place/region/format, DBLP link, acceptance rates, publisher/open-access) is
supplementary - looked up independently of that precedence chain, since a conference can
have e.g. a known acceptance rate regardless of whether its deadline is verified.
"""
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, derive_format, derive_region, load_core_rows, normalize_acronym  # noqa: E402

OVERRIDES_DIR = ROOT / "data" / "overrides"
EXTERNAL_CACHE = ROOT / "data" / "external_cache.json"
ACCEPTANCE_RATES_CACHE = ROOT / "data" / "acceptance_rates.json"
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


def load_json_cache(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def merge(rows, by_id, by_acronym, external_cache, acceptance_rates_cache):
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
                year=None,
                notes=None,
                status="unknown",
                source=None,
                source_url=None,
                updated_by=None,
                checked_at=None,
            )

        # Supplementary fields - independent of the deadline precedence above.
        place = None
        if override and override.get("place"):
            place = override.get("place")
        elif external and external.get("place"):
            place = external.get("place")
        entry.update(
            place=place,
            region=derive_region(place),
            format=derive_format(place),
            dblp_url=(external or {}).get("dblp_url"),
            publisher=(override or {}).get("publisher"),
            open_access=(override or {}).get("open_access"),
            acceptance_rates=acceptance_rates_cache.get(str(row["id"]), []),
            workshops=(override or {}).get("workshops") or [],
        )
        out.append(entry)

    out.sort(key=lambda e: (e["deadline"] is None, e["deadline"] or "", e["acronym"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(out),
        "conferences": out,
    }


def escape_ics(text):
    return re.sub(r"[\\;,]", lambda m: "\\" + m.group(0), text).replace("\n", "\\n")


def ics_event(entry):
    description = " - ".join(filter(None, [entry["title"], entry.get("notes"), entry.get("cfp_url")]))
    summary = f"{entry['acronym']} CFP deadline"
    deadline = date.fromisoformat(entry["deadline"])
    lines = [
        "BEGIN:VEVENT",
        f"UID:{entry['id']}-{entry['deadline']}@core-cfp",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;VALUE=DATE:{deadline.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{(deadline + timedelta(days=1)).strftime('%Y%m%d')}",
        f"SUMMARY:{escape_ics(summary)}",
        f"DESCRIPTION:{escape_ics(description)}",
    ]
    if entry.get("cfp_url"):
        lines.append(f"URL:{entry['cfp_url']}")
    lines.append("END:VEVENT")
    return "\r\n".join(lines)


def write_ics_feed(database, path):
    """A stable-URL companion to the per-view export in site/app.js (buildIcs) - covers
    *all* conferences with a known deadline, so a calendar app can subscribe once and
    keep re-polling it, instead of a one-off download of whatever's currently filtered."""
    events = [ics_event(e) for e in database["conferences"] if e["deadline"]]
    text = "\r\n".join(
        ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//core-cfp//deadlines//EN", "CALSCALE:GREGORIAN", *events, "END:VCALENDAR"]
    )
    path.write_text(text, encoding="utf-8")
    return len(events)


def main():
    rows = load_core_rows()
    overrides = load_overrides()
    external_cache = load_json_cache(EXTERNAL_CACHE)
    acceptance_rates_cache = load_json_cache(ACCEPTANCE_RATES_CACHE)
    by_id, by_acronym = index_overrides(overrides, rows)
    database = merge(rows, by_id, by_acronym, external_cache, acceptance_rates_cache)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(database, indent=2, ensure_ascii=False), encoding="utf-8")
    ics_count = write_ics_feed(database, OUTPUT_JSON.parent / "all.ics")

    counts = {"verified": 0, "community": 0, "unknown": 0}
    for e in database["conferences"]:
        counts[e["status"]] += 1
    with_rates = sum(1 for e in database["conferences"] if e["acceptance_rates"])
    with_dblp = sum(1 for e in database["conferences"] if e["dblp_url"])
    print(
        f"Wrote {database['count']} conferences to {OUTPUT_JSON} "
        f"({counts['verified']} verified, {counts['community']} community-sourced, "
        f"{counts['unknown']} without a known deadline; "
        f"{with_rates} with acceptance-rate data, {with_dblp} with a DBLP link); "
        f"wrote {ics_count} events to {OUTPUT_JSON.parent / 'all.ics'}"
    )


if __name__ == "__main__":
    main()
