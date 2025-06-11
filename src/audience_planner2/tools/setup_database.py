"""
Setup script to convert JSON dataset to DuckDB database
"""
import json
import sys
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[3]
JSON_PATH = ROOT / "segments2.json"
DB_PATH = ROOT / "knowledge" / "segments.duckdb"


def setup_database(json_path: Path, db_path: Path):
    # ensure output folder exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # load JSON
    if not json_path.exists():
        print(f"Error: cannot find {json_path}", file=sys.stderr)
        sys.exit(1)
    segments = json.loads(json_path.read_text())

    # connect to DuckDB (string or Path works)
    conn = duckdb.connect(str(db_path))

    # drop & recreate table
    conn.execute("DROP TABLE IF EXISTS segments")
    conn.execute("""
        CREATE TABLE segments (
            name                  TEXT,
            iconName              TEXT,
            identityGraphName     TEXT,
            taxonomyId            TEXT,
            datasetIds            TEXT,
            quality_score         TEXT,
            recency               TEXT,
            size                  BIGINT,
            age_range             TEXT,
            income_level          TEXT,
            location_type         TEXT,
            category              TEXT,
            confidence            TEXT,
            estReach              BIGINT,
            cpm                   DOUBLE,
            cpmCap                DOUBLE,
            programmaticMediaPct  DOUBLE,
            advertiserDirectPct   DOUBLE,
            dataSource            TEXT,
            metadata              TEXT,
            segmentId             TEXT PRIMARY KEY
        );
    """)

    # insert rows
    inserted = 0
    for seg in segments:
        values = [
            seg.get("name"),
            seg.get("logo", {}).get("metadata", {}).get("iconName"),
            seg.get("identityGraphName"),
            seg.get("taxonomyId"),
            ",".join(seg.get("segmentCriteria", {}).get("datasetIds", [])),
            seg.get("segmentCriteria", {}).get("filters", {}).get("quality_score"),
            seg.get("segmentCriteria", {}).get("filters", {}).get("recency"),
            seg.get("size"),
            seg.get("demographics", {}).get("age_range"),
            seg.get("demographics", {}).get("income_level"),
            seg.get("demographics", {}).get("location_type"),
            seg.get("taxonomyAttributes", {}).get("category"),
            seg.get("taxonomyAttributes", {}).get("confidence"),
            seg.get("estReach"),
            seg.get("cpm"),
            seg.get("cpmCap"),
            seg.get("programmaticMediaPct"),
            seg.get("advertiserDirectPct"),
            seg.get("dataSource"),
            seg.get("metadata"),
            seg.get("segmentId"),
        ]
        try:
            conn.execute(
                "INSERT INTO segments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                values
            )
            inserted += 1
        except Exception as e:
            print(f"[WARN] could not insert {seg.get('name')}: {e}", file=sys.stderr)

    conn.commit()
    conn.close()
    print(f"Inserted {inserted}/{len(segments)} segments into {db_path!r}")


if __name__ == "__main__":
    setup_database(JSON_PATH, DB_PATH)
