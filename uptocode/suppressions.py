"""Structured source suppression directives with auditable metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re

from uptocode.models import AnalysisWarning, SuppressionDetail


_DIRECTIVE = re.compile(r"(?:#|//)\s*uptocode:\s*ignore\s+(AA\d{3})(?P<meta>.*)$")
_TOKEN = re.compile(
    r"(?:owner=(?P<owner>[A-Za-z0-9_.@-]+)|"
    r'reason="(?P<reason>[^"\r\n]*)"|'
    r"expires=(?P<expires>\d{4}-\d{2}-\d{2}))"
)


@dataclass(frozen=True)
class SuppressionDirective:
    detail: SuppressionDetail
    active: bool


class SuppressionIndex:
    def __init__(self, directives: list[SuppressionDirective]) -> None:
        self.directives = directives

    def find(self, rule_id: str, finding_line: int) -> SuppressionDirective | None:
        return next(
            (
                item
                for item in self.directives
                if item.detail.rule == rule_id
                and item.detail.line in {finding_line, finding_line - 1}
            ),
            None,
        )


def parse_suppressions(
    lines: list[str],
    *,
    file: str,
    today: date | None = None,
) -> tuple[SuppressionIndex, list[AnalysisWarning]]:
    scan_date = today or date.today()
    directives: list[SuppressionDirective] = []
    warnings: list[AnalysisWarning] = []
    for line_number, line in enumerate(lines, start=1):
        match = _DIRECTIVE.search(line)
        if match is None:
            continue
        rule_id = match.group(1)
        metadata = match.group("meta").strip()
        values: dict[str, str] = {}
        malformed = False
        if metadata:
            position = 0
            seen: set[str] = set()
            for token in _TOKEN.finditer(metadata):
                if metadata[position : token.start()].strip():
                    malformed = True
                    break
                key = next(key for key in ("owner", "reason", "expires") if token.group(key) is not None)
                if key in seen:
                    malformed = True
                    break
                seen.add(key)
                values[key] = token.group(key)
                position = token.end()
            if metadata[position:].strip() or not values:
                malformed = True
        expiry: date | None = None
        if not malformed and "expires" in values:
            try:
                expiry = date.fromisoformat(values["expires"])
            except ValueError:
                malformed = True
        if malformed:
            values = {}
            expiry = None
            warnings.append(
                AnalysisWarning(
                    code="SUPPRESSION_METADATA_INVALID",
                    message="Suppression metadata is malformed; the directive was treated as bare.",
                    file=file,
                    line=line_number,
                )
            )
        detail = SuppressionDetail(
            file=file,
            line=line_number,
            rule=rule_id,
            owner=values.get("owner"),
            reason=values.get("reason"),
            expires=expiry,
        )
        active = expiry is None or expiry >= scan_date
        directives.append(SuppressionDirective(detail=detail, active=active))
        if expiry is not None and not active:
            warnings.append(
                AnalysisWarning(
                    code="SUPPRESSION_EXPIRED",
                    message=f"Suppression for {rule_id} expired on {expiry.isoformat()}.",
                    file=file,
                    line=line_number,
                )
            )
    return SuppressionIndex(directives), warnings
