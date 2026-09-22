#!/usr/bin/env python3
"""Import real-world deadlines from established community-maintained conference
deadline trackers and match them against our CORE-ranked conference list:

- ccfddl/ccf-deadlines (backs ccfddl.com / aideadlines.org) - covers ~360
  conferences across AI, systems, security, DB, theory, etc., and conveniently
  ships its own CORE rank per conference, which we use to disambiguate.
- The "sec-deadlines" family: sec-deadlines, hci-deadlines, ds-deadlines and
  paperswithcode/ai-deadlines all share the same simple `_data/conferences.yml`
  schema (different Jekyll forks of the same original template).

These projects are actively maintained via their own pull requests, so their
data is generally more reliable than anything we could guess ourselves - but
it is still surfaced on the site as "community-sourced", not "verified", since
nobody in *this* project checked it against the primary CFP page. A verified
override in data/overrides/ always takes precedence. See README.

Writes data/external_cache.json, consumed by build_database.py. Cheap enough
(a handful of HTTP requests) to just rerun in full each time.
"""
import io
import json
import re
import sys
import tarfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_core_rows, normalize_acronym  # noqa: E402

OUTPUT_PATH = ROOT / "data" / "external_cache.json"
USER_AGENT = "corecfp-bot/0.1 (+https://github.com/; importing public conference-deadline datasets)"

CCF_DEADLINES_TARBALL = "https://github.com/ccfddl/ccf-deadlines/archive/refs/heads/main.tar.gz"

# Same "_data/conferences.yml" schema, different branches/subject scopes.
# Priority order: earlier sources win when more than one has data for the
# same conference.
CONFERENCE_DEADLINES_FAMILY = [
    ("sec-deadlines", "sec-deadlines/sec-deadlines.github.io", "master"),
    ("se-deadlines", "se-deadlines/se-deadlines.github.io", "main"),
    ("hci-deadlines", "hci-deadlines/hci-deadlines.github.io", "gh-pages"),
    ("ds-deadlines", "ds-deadlines/ds-deadlines.github.io", "gh-pages"),
    ("ai-deadlines", "paperswithcode/ai-deadlines", "gh-pages"),
]

DEADLINE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")


def normalize_dblp(value):
    """ccf-deadlines ships a bare dblp suffix (e.g. "ccs"); the sec-deadlines family
    sometimes already has a full URL. Normalize both to a full dblp venue URL."""
    value = (value or "").strip()
    if not value:
        return None
    return value if value.startswith("http") else f"https://dblp.org/db/conf/{value}/"


def parse_deadline_str(value):
    value = str(value or "").strip()
    if not value or value.upper() == "TBD":
        return None
    for fmt in DEADLINE_FORMATS:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def build_core_index():
    """normalized acronym -> [{id, acronym, rank}, ...]"""
    index = {}
    for row in load_core_rows():
        index.setdefault(normalize_acronym(row["acronym"]), []).append(row)
    return index


def fetch_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def import_ccf_deadlines(core_index, results):
    print("Fetching ccf-deadlines...")
    raw = fetch_url(CCF_DEADLINES_TARBALL)
    tar = tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz")
    matched = 0
    for member in tar.getmembers():
        if not re.search(r"/conference/[A-Z]+/[^/]+\.yml$", member.name):
            continue
        fileobj = tar.extractfile(member)
        if fileobj is None:
            continue
        try:
            entries = yaml.safe_load(fileobj.read()) or []
        except yaml.YAMLError:
            continue

        for entry in entries:
            title = entry.get("title", "")
            candidates = core_index.get(normalize_acronym(title))
            if not candidates:
                continue
            core_rank = (entry.get("rank") or {}).get("core")
            if len(candidates) > 1:
                narrowed = [c for c in candidates if core_rank and c["rank"] == core_rank]
                if len(narrowed) != 1:
                    print(f"  WARNING: ambiguous ccf-deadlines match for '{title}' - skipping")
                    continue
                match = narrowed[0]
            else:
                match = candidates[0]

            best = None  # (deadline_datetime, conf)
            for conf in entry.get("confs") or []:
                for item in conf.get("timeline") or []:
                    parsed = parse_deadline_str(item.get("deadline"))
                    if parsed is None or parsed < datetime.now(timezone.utc):
                        continue
                    if best is None or parsed < best[0]:
                        best = (parsed, conf)
            if best is None:
                continue
            deadline_dt, conf = best
            results.setdefault(
                str(match["id"]),
                {
                    "source": "ccf-deadlines",
                    "source_url": "https://github.com/ccfddl/ccf-deadlines",
                    "acronym": match["acronym"],
                    "deadline": deadline_dt.date().isoformat(),
                    "timezone": conf.get("timezone"),
                    "cfp_url": conf.get("link"),
                    "event_date": conf.get("date"),
                    "place": conf.get("place"),
                    "dblp_url": normalize_dblp(entry.get("dblp")),
                },
            )
            matched += 1
    print(f"  matched {matched} conferences from ccf-deadlines")


def import_conference_deadlines_family(core_index, results):
    # Two schema variants share this template family: sec-deadlines uses one
    # entry per conference with `name` + a list of deadlines across years;
    # hci/ds/ai-deadlines use one entry per conference-year with `title` +
    # a single `deadline`. Group by normalized acronym first so both shapes
    # are handled the same way.
    for name, repo, branch in CONFERENCE_DEADLINES_FAMILY:
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/_data/conferences.yml"
        print(f"Fetching {name} ({url})...")
        try:
            raw = fetch_url(url)
        except urllib.error.URLError as exc:
            print(f"  failed: {exc}")
            continue
        try:
            entries = yaml.safe_load(raw.decode("utf-8")) or []
        except yaml.YAMLError as exc:
            print(f"  failed to parse: {exc}")
            continue

        groups = {}
        for entry in entries:
            label = entry.get("name") or entry.get("title") or ""
            groups.setdefault(normalize_acronym(label), []).append(entry)

        matched = 0
        for key, group_entries in groups.items():
            candidates = core_index.get(key)
            if not candidates or len(candidates) > 1:
                continue
            match = candidates[0]
            if str(match["id"]) in results:
                continue  # a higher-priority source already matched this conference

            best = None  # (deadline_datetime, entry)
            for entry in group_entries:
                raw_deadline = entry.get("deadline")
                values = raw_deadline if isinstance(raw_deadline, list) else [raw_deadline]
                for value in values:
                    parsed = parse_deadline_str(value)
                    if parsed is None or parsed < datetime.now(timezone.utc):
                        continue
                    if best is None or parsed < best[0]:
                        best = (parsed, entry)
            if best is None:
                continue
            deadline_dt, entry = best
            dblp_raw = next((e.get("dblp") for e in group_entries if e.get("dblp")), None)

            results[str(match["id"])] = {
                "source": name,
                "source_url": f"https://github.com/{repo}",
                "acronym": match["acronym"],
                "deadline": deadline_dt.date().isoformat(),
                "timezone": entry.get("timezone"),
                "cfp_url": entry.get("link"),
                "event_date": entry.get("date"),
                "place": entry.get("place"),
                "dblp_url": normalize_dblp(dblp_raw),
            }
            matched += 1
        print(f"  matched {matched} conferences from {name}")


def main():
    core_index = build_core_index()
    results = {}
    import_ccf_deadlines(core_index, results)
    import_conference_deadlines_family(core_index, results)

    checked_at = datetime.now(timezone.utc).isoformat()
    for entry in results.values():
        entry["checked_at"] = checked_at

    OUTPUT_PATH.write_text(
        json.dumps(results, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    print(f"Wrote {len(results)} externally-sourced deadlines to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
