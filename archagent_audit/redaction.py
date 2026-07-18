"""Irreversible redaction applied before excerpts leave the analyzer."""

from __future__ import annotations

import re

from archagent_audit.models import RedactionCounts


_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai-api-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[A-Z0-9]{16}\b")),
    (
        "bearer-token",
        re.compile(r"(?i)(?<=bearer )[A-Za-z0-9._~+/-]{20,}={0,2}"),
    ),
)


def redact_text(text: str) -> tuple[str, RedactionCounts]:
    """Replace recognized secrets without retaining their values."""
    counts = RedactionCounts()
    redacted = text
    for kind, pattern in _SECRET_PATTERNS:
        redacted, replacements = pattern.subn(f"[REDACTED:{kind}]", redacted)
        counts.secrets += replacements
    return redacted, counts

