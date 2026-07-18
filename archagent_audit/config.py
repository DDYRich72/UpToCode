"""Configuration and source discovery."""

from __future__ import annotations

from pathlib import Path

import pathspec
import yaml
from pydantic import BaseModel, Field


DEFAULT_EXCLUDES = [
    ".git/",
    ".venv/",
    "venv/",
    "node_modules/",
    "__pycache__/",
    ".pytest_cache/",
    "build/",
    "dist/",
    "*.egg-info/",
]


class ScanConfig(BaseModel):
    exclude: list[str] = Field(default_factory=list)
    max_file_size: int = 1024 * 1024


def load_config(root: Path) -> ScanConfig:
    config_path = root / ".archagent-audit.yml"
    if not config_path.exists():
        return ScanConfig()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return ScanConfig.model_validate(raw)


def discover_python_files(root: Path, config: ScanConfig) -> tuple[list[Path], int]:
    patterns = list(DEFAULT_EXCLUDES) + list(config.exclude)
    gitignore = root / ".gitignore"
    if gitignore.exists():
        patterns.extend(gitignore.read_text(encoding="utf-8").splitlines())
    spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    included: list[Path] = []
    skipped = 0
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if spec.match_file(relative) or path.stat().st_size > config.max_file_size:
            skipped += 1
            continue
        included.append(path)
    return included, skipped

