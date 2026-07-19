"""Versioned trusted-local rulepack loading over normalized evidence."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import re
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import Field

from archagent_audit.models import AnalysisWarning, Finding, StrictModel


PLUGIN_API_VERSION = "1.0"
_CUSTOM_ID = re.compile(r"^[A-Z][A-Z0-9_-]*/[A-Z0-9_-]+$")


class NormalizedFileEvidence(StrictModel):
    file: str
    frameworks: list[str] = Field(default_factory=list)
    agent_present: bool = False
    model_call_count: int = 0
    tool_count: int = 0
    loop_count: int = 0


class RuleContext(StrictModel):
    api_version: str = PLUGIN_API_VERSION
    files: list[NormalizedFileEvidence]


class RulePluginResult(StrictModel):
    findings: list[Finding] = Field(default_factory=list)
    warnings: list[AnalysisWarning] = Field(default_factory=list)


@runtime_checkable
class RulePlugin(Protocol):
    api_version: str

    def evaluate(self, context: RuleContext) -> RulePluginResult: ...


def _validate_plugin(plugin: object, source: str) -> RulePlugin:
    if not isinstance(plugin, RulePlugin):
        raise ValueError(f"Rulepack {source} does not implement the RulePlugin protocol")
    if plugin.api_version != PLUGIN_API_VERSION:
        raise ValueError(f"Rulepack {source} uses unsupported API {plugin.api_version}")
    return plugin


def _load_path(path: Path) -> RulePlugin:
    resolved = path.resolve(strict=True)
    spec = importlib.util.spec_from_file_location(
        f"archagent_external_{abs(hash(str(resolved)))}", resolved
    )
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load rulepack {resolved}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return _validate_plugin(getattr(module, "plugin", None), str(resolved))


def load_rule_plugins(entries: list[str], *, root: Path) -> list[RulePlugin]:
    plugins: list[RulePlugin] = []
    installed = {entry.name: entry for entry in importlib.metadata.entry_points(group="archagent_audit.rules")}
    for value in entries:
        if value.startswith("entrypoint:"):
            name = value.partition(":")[2]
            if name not in installed:
                raise ValueError(f"Unknown rulepack entry point: {name}")
            plugins.append(_validate_plugin(installed[name].load(), value))
        else:
            candidate = Path(value)
            plugins.append(_load_path(candidate if candidate.is_absolute() else root / candidate))
    return plugins


def evaluate_plugins(plugins: list[RulePlugin], context: RuleContext) -> RulePluginResult:
    combined = RulePluginResult()
    for plugin in plugins:
        result = RulePluginResult.model_validate(plugin.evaluate(context))
        for finding in result.findings:
            if not _CUSTOM_ID.fullmatch(finding.rule_id):
                raise ValueError(
                    f"Custom rule id {finding.rule_id!r} must use an ORGANIZATION/RULE namespace"
                )
        combined.findings.extend(result.findings)
        combined.warnings.extend(result.warnings)
    return combined
