"""Journal orchestration: LLM -> guard -> (regen once) -> template. Never raises for LLM issues."""
from __future__ import annotations

from collections.abc import Callable

from . import guard as _guard
from . import llm as _llm
from . import prompt as _prompt
from . import template as _template


def write_journal(
    log: dict,
    model_name: str,
    timeout_s: int = 120,
    generate_fn: Callable[[str, str, int], str] | None = None,
) -> tuple[str, str]:
    """Returns (markdown, provenance) where provenance is 'llm:<model>', 'llm-regen:<model>',
    or 'template:<reason>'. generate_fn(model, prompt, timeout) is injectable for tests."""
    gen = generate_fn or _llm.generate
    prompt = _prompt.build_prompt(log)
    known = {d["species_common"] for d in log.get("detections", [])}
    known_sci = {d["species_sci"] for d in log.get("detections", [])}
    try:
        text = gen(model_name, prompt, timeout_s)
        if not text.strip():
            raise _llm.OllamaDown("empty response")
        if _guard.invented_species(text, known, known_sci):
            text2 = gen(model_name, prompt + "\n\nReminder: name ONLY species from the walk log.", timeout_s)
            if _guard.invented_species(text2, known, known_sci):
                return _template.render_template(log), "template:guard-failed-twice"
            return text2, f"llm-regen:{model_name}"
        return text, f"llm:{model_name}"
    except _llm.OllamaDown as exc:
        return _template.render_template(log), f"template:{exc}"
    except Exception as exc:  # never let the journal step crash a walk
        return _template.render_template(log), f"template:unexpected-{type(exc).__name__}"
