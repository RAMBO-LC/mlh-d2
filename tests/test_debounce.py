from fieldnotes.detect.base import Detection
from fieldnotes.store import logic as L


def D(sci, common="X", start=0.0, conf=0.9):
    return Detection(common, sci, conf, start, start + 3.0)


def test_first_ever_first_walk_repeat():
    dets = [D("SciA", "Alpha", 0.0), D("SciA", "Alpha", 60.0),
            D("SciB", "Beta", 120.0), D("SciA", "Alpha", 700.0)]
    out = L.assign_novelty(dets, seen_ever={"SciB"}, debounce_minutes=10)
    assert [n for _, n in out] == [L.FIRST_EVER, L.REPEAT, L.FIRST_THIS_WALK, L.REPEAT]


def test_interleaved_species():
    dets = [D("A", "A", 0.0), D("B", "B", 3.0), D("A", "A", 6.0), D("B", "B", 9.0)]
    out = L.assign_novelty(dets, seen_ever=set(), debounce_minutes=10)
    assert [n for _, n in out] == [L.FIRST_EVER, L.FIRST_EVER, L.REPEAT, L.REPEAT]


def test_empty_input():
    assert L.assign_novelty([], set(), 10) == []


def test_unsorted_input_sorted_by_time():
    dets = [D("A", "A", 30.0), D("A", "A", 0.0)]
    out = L.assign_novelty(dets, set(), 10)
    assert [n for _, n in out] == [L.FIRST_EVER, L.REPEAT]
