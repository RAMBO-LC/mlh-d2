"""Prompt builder: structured log -> constrained prompt. Facts-only, trivia labeled."""
from __future__ import annotations


def build_prompt(log: dict) -> str:
    """log keys: place, date, duration_s, n_windows, detections (list of dicts with
    species_common, species_sci, confidence, start_s, novelty, count), weather_note."""
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
        "5. Detections below 0.5 confidence are uncertain: describe them as "
        '"possibly heard" or "uncertain", never as confirmed.',
        "6. Only name species that appear in the walk log. No other birds.",
        "",
        "WALK LOG (facts — everything you may state as observed):",
        f"Place: {log.get('place', 'unstated location')}",
        f"Date: {log.get('date', 'unstated date')}",
        f"Duration: {log.get('duration_s', 0):.0f} seconds, "
        f"{log.get('n_windows', 0)} analysis windows.",
    ]
    if log.get("weather_note"):
        lines.append(f"Walker's weather note: {log['weather_note']}")
    dets = log.get("detections", [])
    if not dets:
        lines.append("Detections: none above the confidence threshold.")
    else:
        lines.append("Detections:")
        for d in dets:
            conf_word = "uncertain" if d["confidence"] < 0.5 else f"{d['confidence']:.2f}"
            lines.append(
                f"- {d['species_common']} ({d['species_sci']}), heard {d['count']}x, "
                f"confidence {conf_word}, status: {d['novelty']}"
            )
    lines += ["", "Write the journal now (~150 words):"]
    return "\n".join(lines)
