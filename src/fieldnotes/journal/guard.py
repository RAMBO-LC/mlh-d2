"""Hallucination guard: every species named in the journal must exist in the log
(or be inside a sentence flagged 'general knowledge, unverified'). Regenerate once, then template."""
from __future__ import annotations

import re

TRIVIA_FLAG = "general knowledge, unverified"


def uncertain(d: dict) -> bool:
    """Shared confidence wording (template, prompt, web table rule): a species is
    'uncertain' when heard in only one window or its best confidence is below 0.5."""
    return d.get("count", 0) <= 1 or d.get("confidence", 0.0) < 0.5


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def invented_species(
    journal: str,
    log_species_common: set[str],
    log_species_sci: set[str] | None = None,
) -> list[str]:
    """Return journal sentences that name a bird-like phrase that is neither in the log
    (common or scientific name, case-insensitive) nor flagged as trivia. Candidates are
    Title-Case or ALL-CAPS 2-3 word phrases — the shape of English bird names.
    (ALL-CAPS matching added after a test showed shouted invented names slipped through.)"""
    problems: list[str] = []
    known = {s.lower() for s in log_species_common} | {
        s.lower() for s in (log_species_sci or set())
    }
    phrase = re.compile(
        r"\b([A-Z][a-z]+(?: [A-Z][a-z]+){1,2}|[A-Z]{2,}(?: [A-Z]{2,}){1,2})\b"
    )
    for sent in _sentences(journal):
        if TRIVIA_FLAG in sent:
            continue
        for match in phrase.finditer(sent):
            word = match.group(1)
            # Skip the fixed "Species of the day" heading and sentence starts that are generic.
            if word.lower().startswith("species of"):
                continue
            if word.lower() not in known:
                problems.append(f"{word!r} in: {sent[:120]}")
    return problems
