"""Strict configuration and bounded, pruned Python source discovery."""

from __future__ import annotations

import os
from pathlib import Path
import pathspec
import yaml
from pydantic import Field, ValidationError

from uptocode.models import Severity, SkippedFile, StrictModel


DEFAULT_EXCLUDES = [
    ".git/",
    ".venv/",
    ".venv*/",
    "venv/",
    "node_modules/",
    "__pycache__/",
    ".pytest_cache/",
    "build/",
    "dist/",
    "*.egg-info/",
    "generated/",
    "**/generated/",
    "*.generated.py",
    "*_pb2.py",
]


class RuleOverride(StrictModel):
    enabled: bool = True
    severity: Severity | None = None


class JudgmentConfig(StrictModel):
    model: str = "gpt-5.6"
    base_url: str | None = None
    timeout_seconds: float = Field(default=30.0, gt=0, le=240)
    max_output_tokens: int = Field(default=2_000, ge=1, le=16_000)
    rule_call_budget: int = Field(default=6, ge=1, le=12)
    max_retries: int = Field(default=2, ge=0, le=5)


class ScanConfig(StrictModel):
    exclude: list[str] = Field(default_factory=list, max_length=1_000)
    max_file_size: int = Field(default=1024 * 1024, ge=1, le=16 * 1024 * 1024)
    max_total_source_size: int = Field(
        default=4 * 1024 * 1024,
        ge=1,
        le=256 * 1024 * 1024,
    )
    deadline_seconds: float = Field(default=240.0, gt=0, le=3_600)
    rules: dict[str, RuleOverride] = Field(default_factory=dict, max_length=512)
    rulepacks: list[str] = Field(default_factory=list, max_length=32)
    judgment: JudgmentConfig = Field(default_factory=JudgmentConfig)


def load_config(root: Path) -> ScanConfig:
    config_path = root / ".uptocode.yml"
    if not config_path.exists():
        config = ScanConfig()
        return _environment_overrides(config)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return _environment_overrides(ScanConfig.model_validate(raw))
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise ValueError(f"Invalid configuration {config_path}: {error}") from error


def _environment_overrides(config: ScanConfig) -> ScanConfig:
    judgment = config.judgment
    values: dict[str, object] = {}
    if model := os.getenv("UPTOCODE_JUDGMENT_MODEL"):
        values["model"] = model
    if base_url := os.getenv("UPTOCODE_OPENAI_BASE_URL"):
        values["base_url"] = base_url
    numeric = {
        "UPTOCODE_JUDGMENT_TIMEOUT": ("timeout_seconds", float),
        "UPTOCODE_JUDGMENT_MAX_OUTPUT_TOKENS": ("max_output_tokens", int),
        "UPTOCODE_JUDGMENT_RULE_BUDGET": ("rule_call_budget", int),
        "UPTOCODE_JUDGMENT_MAX_RETRIES": ("max_retries", int),
    }
    try:
        for variable, (field, converter) in numeric.items():
            if raw := os.getenv(variable):
                values[field] = converter(raw)
        if values:
            judgment = JudgmentConfig.model_validate({**judgment.model_dump(), **values})
        root_values = config.model_dump()
        root_values["judgment"] = judgment.model_dump()
        if raw_size := os.getenv("UPTOCODE_MAX_FILE_SIZE"):
            root_values["max_file_size"] = int(raw_size)
        if raw_deadline := os.getenv("UPTOCODE_DEADLINE_SECONDS"):
            root_values["deadline_seconds"] = float(raw_deadline)
        return ScanConfig.model_validate(root_values)
    except (TypeError, ValueError, ValidationError) as error:
        raise ValueError(f"Invalid UpToCode environment configuration: {error}") from error


def _pathspec(lines: list[str]) -> pathspec.PathSpec:
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def _matches_nested(
    path: Path,
    *,
    is_directory: bool,
    nested: list[tuple[Path, pathspec.PathSpec]],
) -> bool:
    ignored = False
    for base, spec in nested:
        try:
            relative = path.relative_to(base).as_posix()
        except ValueError:
            continue
        if is_directory:
            relative += "/"
        match = spec.check_file(relative)
        if match.include is not None:
            ignored = bool(match.include)
    return ignored


def discover_python_files_detailed(
    root: Path, config: ScanConfig
) -> tuple[list[Path], list[SkippedFile]]:
    """Discover files without descending into known excluded trees."""
    base_spec = _pathspec(list(DEFAULT_EXCLUDES) + list(config.exclude))
    nested: list[tuple[Path, pathspec.PathSpec]] = []
    included: list[Path] = []
    skipped: list[SkippedFile] = []
    for directory, names, files in os.walk(root, topdown=True):
        directory_path = Path(directory)
        if ".gitignore" in files:
            ignore_path = directory_path / ".gitignore"
            try:
                nested.append(
                    (
                        directory_path,
                        _pathspec(ignore_path.read_text(encoding="utf-8").splitlines()),
                    )
                )
            except (OSError, UnicodeDecodeError):
                pass
        kept_names: list[str] = []
        for name in sorted(names):
            candidate = directory_path / name
            relative = candidate.relative_to(root).as_posix() + "/"
            if base_spec.match_file(relative) or _matches_nested(
                candidate, is_directory=True, nested=nested
            ):
                skipped.append(SkippedFile(path=relative.rstrip("/"), reason="excluded-directory"))
            else:
                kept_names.append(name)
        names[:] = kept_names
        for name in sorted(files):
            if not name.lower().endswith(".py"):
                continue
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            if base_spec.match_file(relative) or _matches_nested(
                path, is_directory=False, nested=nested
            ):
                skipped.append(SkippedFile(path=relative, reason="excluded"))
                continue
            try:
                size = path.stat().st_size
                if size > config.max_file_size:
                    skipped.append(SkippedFile(path=relative, reason="file-too-large"))
                    continue
                with path.open("rb") as handle:
                    if b"\x00" in handle.read(4096):
                        skipped.append(SkippedFile(path=relative, reason="binary"))
                        continue
            except OSError:
                skipped.append(SkippedFile(path=relative, reason="file-stat-error"))
                continue
            included.append(path)
    return sorted(included), sorted(skipped, key=lambda item: (item.path, item.reason))


def discover_python_files(root: Path, config: ScanConfig) -> tuple[list[Path], int]:
    """Backward-compatible discovery count API."""
    files, skipped = discover_python_files_detailed(root, config)
    return files, len(skipped)
