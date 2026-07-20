"""Load and validate the data-driven core rule registry."""

from __future__ import annotations

from importlib.resources import files
from typing import Literal

import yaml
from pydantic import HttpUrl

from uptocode.models import Citation, Severity, StrictModel


class RegistryCitation(StrictModel):
    publisher: str
    title: str
    url: HttpUrl
    status: Literal["normative", "supporting"] = "normative"

    def to_public(self) -> Citation:
        return Citation(
            publisher=self.publisher,
            title=self.title,
            url=str(self.url).rstrip("/"),
            status=self.status,
        )


class RuleDefinition(StrictModel):
    id: str
    name: str
    tier: Literal["static", "judgment", "static+judgment"]
    severity: Severity
    maturity: Literal["stable", "experimental"] = "stable"
    citations: list[RegistryCitation]


def load_core_rules() -> list[RuleDefinition]:
    resource = files("uptocode.rules").joinpath("core.yml")
    raw = yaml.safe_load(resource.read_text(encoding="utf-8"))
    return [RuleDefinition.model_validate(item) for item in raw]


def core_rule_map() -> dict[str, RuleDefinition]:
    return {rule.id: rule for rule in load_core_rules()}


def citations_for(rule_id: str) -> list[Citation]:
    return [item.to_public() for item in core_rule_map()[rule_id].citations]
