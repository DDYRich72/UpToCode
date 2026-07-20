"""Load and validate the data-driven core rule registry."""

from __future__ import annotations

from importlib.resources import files
from typing import Literal

import yaml
from pydantic import HttpUrl

from uptocode.models import Severity, StrictModel


class RuleDefinition(StrictModel):
    id: str
    name: str
    tier: Literal["static", "judgment", "static+judgment"]
    severity: Severity
    citations: list[HttpUrl]


def load_core_rules() -> list[RuleDefinition]:
    resource = files("uptocode.rules").joinpath("core.yml")
    raw = yaml.safe_load(resource.read_text(encoding="utf-8"))
    return [RuleDefinition.model_validate(item) for item in raw]
