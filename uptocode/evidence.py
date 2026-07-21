"""Language-neutral evidence emitted by source and framework adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from uptocode.models import AnalysisWarning


Confidence = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class LoopEvidence:
    line: int
    framework: str
    bound_kind: str
    detail: str
    end_line: int | None = None
    provenance: str = "syntax"
    confidence: Confidence = "high"


@dataclass(frozen=True)
class ModelCallEvidence:
    line: int
    framework: str
    has_output_limit: bool
    has_timeout: bool
    has_retry: bool
    has_backoff: bool
    end_line: int | None = None
    provenance: str = "call"
    confidence: Confidence = "high"


@dataclass(frozen=True)
class ToolEvidence:
    line: int
    framework: str
    name: str
    destructive: bool = False
    approval: bool = False
    argument_risk: bool = False
    end_line: int | None = None
    provenance: str = "definition"
    confidence: Confidence = "high"


@dataclass
class NormalizedEvidence:
    language: str
    frameworks: set[str] = field(default_factory=set)
    loops: list[LoopEvidence] = field(default_factory=list)
    model_calls: list[ModelCallEvidence] = field(default_factory=list)
    tools: list[ToolEvidence] = field(default_factory=list)
    warnings: list[AnalysisWarning] = field(default_factory=list)
    agent_present: bool = False
    first_agent_line: int = 1
    has_run_budget: bool = False
    observability_lines: list[int] = field(default_factory=list)

    def merge(self, other: "NormalizedEvidence") -> None:
        if other.agent_present and not self.agent_present:
            self.first_agent_line = other.first_agent_line
        elif other.agent_present:
            self.first_agent_line = min(self.first_agent_line, other.first_agent_line)
        self.agent_present = self.agent_present or other.agent_present
        self.has_run_budget = self.has_run_budget or other.has_run_budget
        self.frameworks.update(other.frameworks)
        self.loops.extend(other.loops)
        self.model_calls.extend(other.model_calls)
        self.tools.extend(other.tools)
        self.warnings.extend(other.warnings)
        self.observability_lines.extend(other.observability_lines)
