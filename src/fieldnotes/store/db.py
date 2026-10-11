"""SQLite storage: walks, detections, clips, life_list. Migrations included (v1)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS walks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    started_at TEXT NOT NULL,
    duration_s REAL NOT NULL,
    lat REAL, lon REAL, week INTEGER,
    model_name TEXT NOT NULL, model_version TEXT NOT NULL,
    config_json TEXT NOT NULL,
    screen_on_s REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    walk_id INTEGER NOT NULL REFERENCES walks(id),
    species_common TEXT NOT NULL, species_sci TEXT NOT NULL,
    confidence REAL NOT NULL, start_s REAL NOT NULL, end_s REAL NOT NULL,
    novelty TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS clips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    walk_id INTEGER NOT NULL REFERENCES walks(id),
    species_common TEXT NOT NULL, path TEXT NOT NULL,
    start_s REAL NOT NULL, end_s REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS life_list (
    species_sci TEXT PRIMARY KEY,
    species_common TEXT NOT NULL,
    first_seen TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_det_walk ON detections(walk_id);
"""


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA_V1)
    try:  # migration v1->v2: per-walk "my own recording" flag (default off)
        con.execute("ALTER TABLE walks ADD COLUMN is_own_recording INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError as exc:
        if "duplicate column" not in str(exc).lower():
            raise
    return con


def add_walk(con: sqlite3.Connection, **fields) -> int:
    fields.setdefault("config_json", "{}")
    cols = ", ".join(fields)
    cur = con.execute(f"INSERT INTO walks ({cols}) VALUES ({','.join('?' for _ in fields)})",
                      tuple(fields.values()))
    return cur.lastrowid


def add_detection(con: sqlite3.Connection, walk_id: int, novelty: str, d) -> int:
    cur = con.execute(
        "INSERT INTO detections (walk_id, species_common, species_sci, confidence,"
        " start_s, end_s, novelty) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (walk_id, d.species_common, d.species_sci, d.confidence, d.start_s, d.end_s, novelty),
    )
    return cur.lastrowid


def add_clip(con: sqlite3.Connection, walk_id: int, species_common: str, path: str,
             start_s: float, end_s: float) -> int:
    cur = con.execute(
        "INSERT INTO clips (walk_id, species_common, path, start_s, end_s) VALUES (?,?,?,?,?)",
        (walk_id, species_common, path, start_s, end_s),
    )
    return cur.lastrowid


def mark_seen(con: sqlite3.Connection, sci: str, common: str, when: str) -> bool:
    """Insert into life list. Returns True if first-ever sighting."""
    row = con.execute("SELECT 1 FROM life_list WHERE species_sci=?", (sci,)).fetchone()
    if row:
        return False
    con.execute(
        "INSERT INTO life_list (species_sci, species_common, first_seen) VALUES (?,?,?)",
        (sci, common, when),
    )
    return True


def life_list(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(con.execute("SELECT * FROM life_list ORDER BY first_seen"))


def walk_detections(con: sqlite3.Connection, walk_id: int) -> list[sqlite3.Row]:
    return list(
        con.execute("SELECT * FROM detections WHERE walk_id=? ORDER BY start_s", (walk_id,))
    )


def wipe_all(db_path: str, clips_dir: str) -> None:
    """Delete all data: the database file and every saved clip. Used by CLI + web button."""
    import shutil

    if Path(db_path).exists():
        Path(db_path).unlink()
    clips = Path(clips_dir)
    if clips.exists():
        shutil.rmtree(clips)
    clips.mkdir(parents=True, exist_ok=True)


def config_snapshot(cfg: dict) -> str:
    return json.dumps(cfg, sort_keys=True)
