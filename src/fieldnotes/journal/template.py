"""Template journal: deterministic fallback when Ollama is missing/times out or guard fails twice."""
from __future__ import annotations


def render_template(log: dict) -> str:
    dets = log.get("detections", [])
    n = len(dets)
    total_hearings = sum(d["count"] for d in dets)
    if n == 0:
        species_part = (
            "No calls cleared the confidence threshold on this walk — "
            "which is data too. Quiet walks happen, especially midday or in wind."
        )
        species_of_day = "None today — the walk itself was the find."
    else:
        top = max(dets, key=lambda d: (d["count"], d["confidence"]))
        names = ", ".join(
            f"{d['species_common']} ({d['count']}x"
            + (", uncertain" if d["confidence"] < 0.5 else "") + ")"
            for d in sorted(dets, key=lambda d: -d["count"])
        )
        species_part = (
            f"We logged {total_hearings} hearings across {n} species: {names}."
        )
        species_of_day = (
            f"{top['species_common']} ({top['species_sci']}) — heard {top['count']}x"
            + (" (uncertain ID, verify the saved clip by ear)" if top["confidence"] < 0.5 else "")
            + "."
        )
    return (
        f"# Field journal — {log.get('date', 'undated walk')}\n\n"
        f"A {float(log.get('duration_s', 0)):.0f}-second walk, phone in pocket, eyes up. "
        f"{species_part}\n\n"
        f"**Species of the day:** {species_of_day}\n\n"
        f"**Next outing:** go 30 minutes earlier, stand still for 10 quiet minutes, "
        f"and count distinct calls before checking the screen.\n\n"
        f"_Written from the detection log by the offline template (no LLM used)._"
    )
