from fieldnotes.detect.base import Detection
from fieldnotes.store import db


def _con(tmp_path):
    return db.connect(str(tmp_path / "t.db"))


def test_db_round_trip(tmp_path):
    con = _con(tmp_path)
    try:
        wid = db.add_walk(con, source_file="w.wav", started_at="2026-10-11",
                          duration_s=9.0, lat=None, lon=None, week=41,
                          model_name="birdnet", model_version="v", config_json="{}")
        d = Detection("Alpha", "SciA", 0.8, 0.0, 3.0)
        db.add_detection(con, wid, "first_ever", d)
        assert db.mark_seen(con, "SciA", "Alpha", "2026-10-11") is True
        assert db.mark_seen(con, "SciA", "Alpha", "2026-10-11") is False
        rows = db.walk_detections(con, wid)
        assert len(rows) == 1 and rows[0]["species_sci"] == "SciA"
        assert [r["species_sci"] for r in db.life_list(con)] == ["SciA"]
        con.commit()
    finally:
        con.close()


def test_wipe_deletes_db_and_clips(tmp_path):
    dbp = str(tmp_path / "x.db")
    clips = str(tmp_path / "clips")
    con = db.connect(dbp)
    con.close()
    (tmp_path / "clips" / "walk_1").mkdir(parents=True)
    (tmp_path / "clips" / "walk_1" / "a.wav").write_bytes(b"RIFF....")
    db.wipe_all(dbp, clips)
    import os

    assert not os.path.exists(dbp)
    assert os.path.isdir(clips) and os.listdir(clips) == []


def test_insert_counts_match_columns(tmp_path):
    """Regression: every INSERT lists as many placeholders as columns (7-col bug)."""
    from fieldnotes.detect.base import Detection

    con = _con(tmp_path)
    try:
        wid = db.add_walk(con, source_file="w.wav", started_at="2026-10-11",
                          duration_s=9.0, lat=1.0, lon=2.0, week=5,
                          model_name="m", model_version="v", config_json="{}")
        d = Detection("Alpha", "SciA", 0.31, 1.0, 4.0)
        assert isinstance(db.add_detection(con, wid, "first_ever", d), int)
        assert isinstance(db.add_clip(con, wid, "Alpha", "/tmp/x.wav", 1.0, 4.0), int)
        assert db.mark_seen(con, "SciA", "Alpha", "2026-10-11") is True
        assert len(db.walk_detections(con, wid)) == 1
        con.commit()
    finally:
        con.close()


def test_wipe_twice_is_safe(tmp_path):
    dbp = str(tmp_path / "x.db")
    clips = str(tmp_path / "clips")
    db.connect(dbp).close()
    db.wipe_all(dbp, clips)
    db.wipe_all(dbp, clips)  # second run must not raise
    import os

    assert not os.path.exists(dbp) and os.listdir(clips) == []
