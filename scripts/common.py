"""Shared constants and CORE-rankings loader for the corecfp data pipeline."""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE_CSV = ROOT / "data" / "core_rankings.csv"

# Only these CORE ranks are included in the site (see project README for rationale).
INCLUDED_RANKS = {"A*", "A", "B"}

# ANZSRC 2020 four-digit "for" codes under division 46 (Information and Computing
# Sciences) that show up in the CORE export. Anything not listed here is shown
# as-is (raw code) rather than guessed at.
FOR_CODE_NAMES = {
    "46": "Information and Computing Sciences (general)",
    "4601": "Applied Computing",
    "4602": "Artificial Intelligence",
    "4603": "Computer Vision and Multimedia Computation",
    "4604": "Cybersecurity and Privacy",
    "4605": "Data Management and Data Science",
    "4606": "Distributed Computing and Systems Software",
    "4607": "Graphics, Augmented Reality and Games",
    "4608": "Human-Centred Computing",
    "4609": "Information Systems",
    "4610": "Library and Information Studies",
    "4611": "Machine Learning",
    "4612": "Software Engineering",
    "4613": "Theory of Computation",
}


def normalize_acronym(text: str) -> str:
    """Fold a conference name down to bare alphanumerics for fuzzy matching,
    e.g. "S&P (Oakland)" and "SP" both normalize to "SP"."""
    text = re.split(r"[\(\[]", text)[0]  # drop "(Oakland)"-style suffixes
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def load_core_rows(csv_path=CORE_CSV):
    """Read data/core_rankings.csv, filtered to INCLUDED_RANKS. This is the
    single source of truth for "which conferences are on the site" - every
    script that needs the CORE list (build_database, import_external) reads
    it through here rather than re-parsing the CSV."""
    rows = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for r in csv.reader(f):
            if len(r) < 5:
                continue
            core_id, title, acronym, source, rank = r[0], r[1], r[2], r[3], r[4]
            if rank not in INCLUDED_RANKS:
                continue
            for_codes = [c for c in r[6:9] if c]
            rows.append(
                {
                    "id": int(core_id),
                    "title": title.strip(),
                    "acronym": acronym.strip(),
                    "rank": rank,
                    "source": source,
                    "field_of_research": [
                        {"code": c, "name": FOR_CODE_NAMES.get(c, c)} for c in for_codes
                    ],
                }
            )
    return rows
