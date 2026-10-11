"""Debounce / novelty: first-ever vs first-this-walk vs repeat (all tested)."""
from __future__ import annotations

from ..detect.base import Detection

FIRST_EVER = "first_ever"
FIRST_THIS_WALK = "first_this_walk"
REPEAT = "repeat"


def assign_novelty(
    detections: list[Detection],
    seen_ever: set[str],
    debounce_minutes: float,
) -> list[tuple[Detection, str]]:
    """Label each detection: first_ever (never in life list), first_this_walk (in life
    list, first time this walk), repeat (otherwise). Every detection is stored in the
    DB regardless — novelty only drives clips + recap emphasis.

    debounce_minutes is reserved for live re-announcement pacing (no live mode in MVP);
    it is validated config, currently not consumed here. See docs/DECISIONS.md.
    """
    _ = debounce_minutes
    out: list[tuple[Detection, str]] = []
    seen_this_walk: set[str] = set()
    for d in sorted(detections, key=lambda x: x.start_s):
        if d.species_sci in seen_this_walk:
            out.append((d, REPEAT))
        elif d.species_sci in seen_ever:
            out.append((d, FIRST_THIS_WALK))
            seen_this_walk.add(d.species_sci)
        else:
            out.append((d, FIRST_EVER))
            seen_this_walk.add(d.species_sci)
            seen_ever.add(d.species_sci)
    return out
