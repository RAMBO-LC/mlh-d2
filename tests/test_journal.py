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

    def log_with(conf, count=3):
        return {"date": "d", "duration_s": 3, "n_windows": 1, "detections": [
            {"species_common": "A B", "species_sci": "A b", "confidence": conf,
             "count": count, "novelty": "first_ever", "start_s": 0.0}]}

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


def _log2(**over):
    log = {"date": "2026-10-11", "duration_s": 24, "n_windows": 8,
           "own_recording": False, "weather_note": "",
           "scope": {"date": "2026-10-11", "location_filter": "off",
                     "threshold": 0.3},
           "detections": [
               {"species_common": "Eurasian Blackbird", "species_sci": "Turdus merula",
                "confidence": 1.0, "count": 4, "novelty": "first_ever", "start_s": 0.0},
               {"species_common": "Lone Tit", "species_sci": "Tit lonely",
                "confidence": 0.9, "count": 1, "novelty": "first_ever", "start_s": 9.0}]}
    log.update(over)
    return log


def test_template_own_flag_wording():
    from fieldnotes.journal import template as T

    off = T.render_template(_log2(own_recording=False))
    assert "A 24-second recording." in off and "phone in pocket" not in off
    on = T.render_template(_log2(own_recording=True))
    assert "A 24-second walk, phone in pocket, eyes up." in on


def test_template_window_counts_not_hearings():
    from fieldnotes.journal import template as T

    md = T.render_template(_log2())
    assert "hear" not in md.lower().replace("heard", "X").replace("hearings", "X")
    assert "detected in 4 of 8 listening windows" in md
    assert "highest confidence 1.00" in md


def test_template_uncertain_single_window_and_low_conf():
    from fieldnotes.journal import template as T

    md = T.render_template(_log2())
    lone = [l for l in md.splitlines() if "Lone Tit" in l][0]
    assert "(uncertain)" in lone  # single window despite 0.9
    low = _log2(detections=[
        {"species_common": "Dim Finch", "species_sci": "Finch dim",
         "confidence": 0.4, "count": 5, "novelty": "x", "start_s": 0.0}])
    assert "(uncertain)" in T.render_template(low)


def test_scope_line_no_coordinates():
    from fieldnotes.journal import writer as W

    md, _ = W.write_journal(_log2(), "m", generate_fn=lambda *a: "Eurasian Blackbird ok. Go again.")
    assert "location filtering off" in md and "threshold 0.3" in md
    assert "60.17" not in md and "24.94" not in md


def test_prompt_window_wording_and_own_rules():
    from fieldnotes.journal import prompt as P

    p = P.build_prompt(_log2())
    assert "hearings" not in p.replace("never 'hearings'", "")
    assert "listening windows" in p
    assert "detected in 4 of 8 listening windows" in p
    assert "heard 4x" not in p
    assert "Never write 'phone in pocket" in p
    p2 = P.build_prompt(_log2(own_recording=True))
    assert "may include the phrase 'phone in pocket" in p2
