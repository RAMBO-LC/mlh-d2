"""Journal: prompt constraints, guard (incl. invented-species catch), fallbacks."""
from fieldnotes.journal import guard, prompt, template, writer
from fieldnotes.journal.llm import OllamaDown


def _log():
    return {
        "place": "37.770,-122.410", "date": "2026-10-11", "duration_s": 600,
        "n_windows": 200, "weather_note": "cool",
        "detections": [
            {"species_common": "Anna's Hummingbird", "species_sci": "Calypte anna",
             "confidence": 0.85, "count": 4, "novelty": "first_ever", "start_s": 3.0},
            {"species_common": "Dark-Eyed Junco", "species_sci": "Junco hyemalis",
             "confidence": 0.32, "count": 1, "novelty": "first_ever", "start_s": 90.0},
        ],
    }


def test_prompt_uses_only_log_facts_and_labels_trivia():
    p = prompt.build_prompt(_log())
    assert "Anna's Hummingbird" in p and "Dark-Eyed Junco" in p
    assert "general knowledge, unverified" in p
    assert "uncertain" in p and "150" in p
    assert "Species of the day" in p or "species of the day" in p


def test_guard_passes_clean_journal():
    j = ("We heard Anna's Hummingbird four times. Species of the day: Anna's Hummingbird. "
         "Next outing: go earlier.")
    assert guard.invented_species(j, {"Anna's Hummingbird", "Dark-Eyed Junco"}) == []


def test_guard_catches_invented_species():
    j = ("We heard Anna's Hummingbird. A Bald Eagle soared overhead. "
         "Next outing: go earlier.")
    problems = guard.invented_species(j, {"Anna's Hummingbird"})
    assert any("Bald Eagle" in p for p in problems)


def test_guard_ignores_flagged_trivia():
    j = ("Anna's Hummingbird visited. The Bald Eagle (general knowledge, unverified) "
         "can see far. Next outing: go earlier.")
    assert guard.invented_species(j, {"Anna's Hummingbird"}) == []


def test_regenerate_once_then_template():
    calls = {"n": 0}

    def gen(model, pr, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return "We saw Anna's Hummingbird and a Bald Eagle. Go again."
        return "Anna's Hummingbird again, no eagles. Go earlier tomorrow."

    md, prov = writer.write_journal(_log(), "test-model", generate_fn=gen)
    assert prov == "llm-regen:test-model"
    assert "Bald Eagle" not in md


def test_double_guard_failure_falls_back_to_template():
    md, prov = writer.write_journal(
        _log(), "m", generate_fn=lambda *a: "Bald Eagle everywhere.")
    assert prov == "template:guard-failed-twice"
    assert "Anna's Hummingbird" in md


def test_ollama_down_falls_back_to_template():
    def gen(*a):
        raise OllamaDown("not running")

    md, prov = writer.write_journal(_log(), "gemma3:4b", generate_fn=gen)
    assert prov.startswith("template:")
    assert "Species of the day" in md


def test_template_handles_empty_log_and_low_confidence():
    log = {"date": "2026-10-11", "duration_s": 60, "detections": []}
    md = template.render_template(log)
    assert "No calls cleared" in md and "Next outing" in md
    log2 = dict(log, detections=[{"species_common": "X", "species_sci": "Y",
                                  "confidence": 0.2, "count": 1}])
    assert "uncertain" in template.render_template(log2)


def test_confidence_word_boundaries():
    from fieldnotes.journal import prompt as P

    def log_with(conf):
        return {"date": "d", "duration_s": 3, "n_windows": 1, "detections": [
            {"species_common": "A B", "species_sci": "A b", "confidence": conf,
             "count": 1, "novelty": "first_ever", "start_s": 0.0}]}

    assert "uncertain" in P.build_prompt(log_with(0.0))
    assert "uncertain" in P.build_prompt(log_with(0.4999))
    line = [l for l in P.build_prompt(log_with(0.5)).splitlines() if l.startswith("- ")][0]
    assert "uncertain" not in line and "0.50" in line
    # NOTE (MVP scope): the only confidence wording is "uncertain" vs the number.
    # "likely"/"confident" TTS words were cut with live mode — no such mapping exists.


def test_guard_scientific_and_case_insensitive():
    assert guard.invented_species("Acanthis cabaret visited.", {"Lesser Redpoll"},
                                  {"Acanthis cabaret"}) == []
    # Title-Case variant of the scientific name is exempt via the sci set…
    assert guard.invented_species("Acanthis Cabaret visited.", {"Lesser Redpoll"},
                                  {"Acanthis cabaret"}) == []
    # …but flags without it:
    assert guard.invented_species("Acanthis Cabaret visited.", {"Lesser Redpoll"}) != []
    assert guard.invented_species("LESSER REDPOLL again.", {"Lesser Redpoll"}) == []
    bad = guard.invented_species("A BALD EAGLE soared.", {"Lesser Redpoll"})
    assert any("BALD EAGLE" in p for p in bad)


def test_fallback_on_timeout_and_empty():
    def timeout_gen(*a):
        raise TimeoutError("slow")

    md, prov = writer.write_journal(_log(), "m", generate_fn=timeout_gen)
    assert prov.startswith("template:") and "Anna's Hummingbird" in md

    md2, prov2 = writer.write_journal(_log(), "m", generate_fn=lambda *a: "   ")
    assert prov2.startswith("template:") and "Species of the day" in md2


def test_zero_detection_journal_invents_nothing():
    from fieldnotes.journal import template as T

    md = T.render_template({"date": "2026-10-11", "duration_s": 9, "detections": []})
    assert guard.invented_species(md, set()) == []


def test_prompt_names_only_logged_species():
    from fieldnotes.journal import prompt as P

    p = P.build_prompt(_log())
    assert "Bald Eagle" not in p and "Blue Jay" not in p
    assert "Anna's Hummingbird" in p and "Dark-Eyed Junco" in p
