"""Stable public identities for findings and rulepack/configuration content."""

from __future__ import annotations

import hashlib
import re


_SPACE = re.compile(r"\s+")


def normalized_text(value: str) -> str:
    return _SPACE.sub(" ", value.strip())


def finding_fingerprint(
    rule_id: str,
    file: str,
    kind: str,
    *,
    detail: str = "",
    excerpt: str = "",
) -> str:
    payload = "|".join(
        (
            rule_id.upper(),
            file.replace("\\", "/").lower(),
            kind,
            normalized_text(detail),
            normalized_text(excerpt),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def content_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
