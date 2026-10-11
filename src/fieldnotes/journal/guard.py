"""Hallucination guard: every species named in the journal must exist in the log
(or be inside a sentence flagged 'general knowledge, unverified'). Regenerate once, then template."""
from __future__ import annotations

import re

TRIVIA_FLAG = "general knowledge, unverified"


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def invented_species(journal: str, log_species_common: set[str]) -> list[str]:
    """Return journal sentences that name a Capitalized common-name-like phrase that is
    neither in the log nor flagged as trivia. Conservative: checks two-word capitalized
    phrases (how English bird names are written) against the log's species list."""
    problems: list[str] = []
    known = {s.lower() for s in log_species_common}
    for sent in _sentences(journal):
        if TRIVIA_FLAG in sent:
            continue
        for match in re.finditer(r"\b([A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?)\b", sent):
            phrase = match.group(1)
            # Skip the fixed "Species of the day" heading and sentence starts that are generic.
            if phrase.lower().startswith("species of"):
                continue
            if phrase.lower() not in known:
                problems.append(f"{phrase!r} in: {sent[:120]}")
    return problems
