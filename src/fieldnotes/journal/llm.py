"""Ollama client over stdlib HTTP (no extra dependency). Localhost only — offline-safe."""
from __future__ import annotations

import json
import urllib.request

OLLAMA_HOST = "http://localhost:11434"


class OllamaDown(Exception):
    pass


def list_models(timeout_s: int = 5) -> list[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        raise OllamaDown(
            "Ollama is not running (tried localhost:11434). Start it with `ollama serve`, "
            "or use the built-in template journal (automatic fallback)."
        ) from exc
    return [m.get("name", "") for m in data.get("models", [])]


def pick_model(configured: str, timeout_s: int = 5) -> str:
    """Use the configured model if installed, else the best installed fallback (prefers gemma)."""
    installed = list_models(timeout_s)
    if configured in installed:
        return configured
    for cand in sorted(installed):
        if "gemma" in cand.lower():
            return cand
    if installed:
        return sorted(installed)[0]
    raise OllamaDown(
        f"Ollama is running but no models are installed. Pull one once, e.g.: "
        f"`ollama pull {configured}` (needs network once, then works offline)."
    )


def generate(model: str, prompt: str, timeout_s: int = 120) -> str:
    body = json.dumps(
        {"model": model, "prompt": prompt, "stream": False,
         "options": {"temperature": 0.7, "num_predict": 400}}
    ).encode()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate", data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode()).get("response", "").strip()
    except TimeoutError as exc:
        raise OllamaDown(
            f"Ollama timed out after {timeout_s}s (model {model}). "
            "Falling back to the template journal."
        ) from exc
    except OllamaDown:
        raise
    except Exception as exc:
        raise OllamaDown(f"Ollama request failed: {exc}. Falling back to template.") from exc
