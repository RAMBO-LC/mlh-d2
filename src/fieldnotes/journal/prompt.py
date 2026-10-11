"""Prompt builder: structured log -> constrained prompt. Facts-only, trivia labeled."""
from __future__ import annotations


def build_prompt(log: dict) -> str:
    """log keys: place, date, duration_s, n_windows, own_recording, detections (list of
    dicts with species_common, species_sci, confidence, count, novelty, start_s), weather_note."""
    own = log.get("own_recording", False)
    n = log.get("n_windows", 0)
    lines = [
        "You are writing a short field journal for a nature walk. "
        "Use ONLY the facts in the walk log below. Never invent sightings, places, or times.",
        "",
        "You MUST follow these rules:",
        "1. About 150 words, warm tone, first person plural or second person.",
        '2. Name a "Species of the day" (the most interesting detection in the log).',
        "3. End with one concrete suggestion for the next outing.",
        '4. Any general natural-history trivia NOT in the log must be labeled exactly: '
        '"general knowledge, unverified".',
        "5. A species detected in only one listening window, or with highest confidence "
        'below 0.5, is uncertain: describe it as "uncertain", never as confirmed.',
        "6. Only name species that appear in the walk log. No other birds.",
        f"7. Open with exactly: 'A {float(log.get('duration_s', 0)):.0f}-second "
        + ("walk" if own else "recording")
        + ".'"
        + ("" if own else " This is a third-party recording, not the writer's own walk."),
        "8. Count detections in listening windows (e.g. 'detected in 3 of 8 listening "
        "windows'), never 'hearings'. Report each species' highest confidence.",
    ]
    if own:
        lines.append("9. You may include the phrase 'phone in pocket, eyes up' once. "
                     "Otherwise never write it.")
    else:
        lines.append("9. Never write 'phone in pocket, eyes up' — the writer was not there.")
    lines += [
        "",
        "WALK LOG (facts — everything you may state as observed):",
        f"Date: {log.get('date', 'unstated date')}",
        f"Duration: {float(log.get('duration_s', 0)):.0f} seconds, "
        f"{n} listening windows analyzed.",
    ]
    if log.get("weather_note"):
        lines.append(f"Walker's weather note: {log['weather_note']}")
    dets = log.get("detections", [])
    if not dets:
        lines.append("Detections: none above the confidence threshold.")
    else:
        lines.append("Detections:")
        for d in dets:
            tag = "uncertain" if (d["count"] <= 1 or d["confidence"] < 0.5) else f"{d['confidence']:.2f}"
            lines.append(
                f"- {d['species_common']} ({d['species_sci']}), detected in "
                f"{d['count']} of {n} listening windows, "
                f"highest confidence {tag}, status: {d['novelty']}"
            )
    lines += ["", "Write the journal now (~150 words):"]
    return "\n".join(lines)
