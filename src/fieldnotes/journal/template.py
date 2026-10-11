"""Template journal: deterministic fallback when Ollama is missing/times out or guard fails twice."""
from __future__ import annotations

from .guard import uncertain as _uncertain


def species_line(d: dict, n_windows: int) -> str:
    conf = f"{d['confidence']:.2f}"
    s = (f"{d['species_common']} ({d['species_sci']}) — detected in "
         f"{d['count']} of {n_windows} listening windows, "
         f"highest confidence {conf}")
    if _uncertain(d):
        s += " (uncertain)"
    return s + "."


def render_template(log: dict) -> str:
    dets = sorted(log.get("detections", []), key=lambda d: -d["count"])
    n = log.get("n_windows", 0)
    dur = float(log.get("duration_s", 0))
    kind = "walk" if log.get("own_recording") else "recording"
    opening = f"A {dur:.0f}-second {kind}"
    if log.get("own_recording"):
        opening += ", phone in pocket, eyes up"
    opening += "."
    if not dets:
        species_part = (
            "No calls cleared the confidence threshold — "
            "which is data too. Quiet walks happen, especially midday or in wind."
        )
        species_of_day = "None today — the walk itself was the find."
    else:
        species_part = " ".join(species_line(d, n) for d in dets)
        top = dets[0]
        species_of_day = f"{top['species_common']} ({top['species_sci']})"
        if _uncertain(top):
            species_of_day += " (uncertain ID — verify the saved clip by ear)"
        species_of_day += "."
    return (
        f"# Field journal — {log.get('date', 'undated walk')}\n\n"
        f"{opening} {species_part}\n\n"
        f"**Species of the day:** {species_of_day}\n\n"
        f"**Next outing:** go 30 minutes earlier, stand still for 10 quiet minutes, "
        f"and count distinct calls before checking the screen.\n\n"
        f"_Written from the detection log by the offline template (no LLM used)._"
    )
