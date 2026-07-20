"""Portable report sanitization for sharing outside the scanned environment."""

from __future__ import annotations

import re
from typing import Any

from uptocode.models import Report


_ABSOLUTE_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/])[^\s\"'<>]*"),
    re.compile(r"(?<![\\])\\\\[^\\\s]+\\[^\s\"'<>]*"),
    re.compile(r"(?<![A-Za-z0-9])/(?:home|Users)/[^/\s]+(?:/[^\s\"'<>]*)?"),
)


def _scrub_text(value: str, roots: tuple[str, ...]) -> str:
    result = value
    for root in sorted((item for item in roots if item), key=len, reverse=True):
        result = result.replace(root, "<scan-root>")
    for pattern in _ABSOLUTE_PATTERNS:
        result = pattern.sub("<absolute-path>", result)
    return result


def _scrub(value: Any, roots: tuple[str, ...]) -> Any:
    if isinstance(value, str):
        return _scrub_text(value, roots)
    if isinstance(value, list):
        return [_scrub(item, roots) for item in value]
    if isinstance(value, dict):
        return {key: _scrub(item, roots) for key, item in value.items()}
    return value


def make_share_safe(report: Report) -> Report:
    roots = (
        report.scan_root,
        report.scan_root.replace("\\", "/"),
        report.scan_root.replace("/", "\\"),
    )
    payload = _scrub(report.model_dump(mode="python"), roots)
    payload["scan_root"] = "<scan-root>"
    return Report.model_validate(payload)
