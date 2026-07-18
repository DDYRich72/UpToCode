"""Load and validate the data-driven core rule registry."""

from __future__ import annotations

from importlib.resources import files

import yaml
from pydantic import BaseModel, HttpUrl

from archagent_audit.models import Severity


class RuleDefinition(BaseModel):
    id: str
    name: str
    tier: str
    severity: Severity
    citations: list[HttpUrl]


def load_core_rules() -> list[RuleDefinition]:
    resource = files("archagent_audit.rules").joinpath("core.yml")
    raw = yaml.safe_load(resource.read_text(encoding="utf-8"))
    return [RuleDefinition.model_validate(item) for item in raw]

