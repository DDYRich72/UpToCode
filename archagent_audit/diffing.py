"""Validated unified-diff reconstruction with fail-closed context handling."""

from __future__ import annotations

import re

from archagent_audit.models import StrictModel


_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchedFile(StrictModel):
    old_path: str | None
    new_path: str | None
    source: str
    deleted: bool = False


class DiffReconstructionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _header_path(value: str) -> str | None:
    path = value.split("\t", 1)[0].strip()
    if path == "/dev/null":
        return None
    if path.startswith(("a/", "b/")):
        path = path[2:]
    if not path or path.startswith("/") or ".." in path.replace("\\", "/").split("/"):
        raise DiffReconstructionError("INVALID_DIFF_PATH", "Diff paths must be relative and contained.")
    return path.replace("\\", "/")


def _apply_hunks(
    lines: list[str],
    index: int,
    base: list[str],
) -> tuple[list[str], int]:
    output: list[str] = []
    old_cursor = 0
    saw_hunk = False
    while index < len(lines) and not lines[index].startswith("--- "):
        match = _HUNK.match(lines[index])
        if not match:
            index += 1
            continue
        saw_hunk = True
        old_start = int(match.group(1))
        old_count = int(match.group(2) or "1")
        old_index = max(0, old_start - 1)
        if old_index < old_cursor or old_index > len(base):
            raise DiffReconstructionError("INVALID_DIFF_HUNK", "Diff hunk range is invalid.")
        output.extend(base[old_cursor:old_index])
        old_cursor = old_index
        consumed = 0
        index += 1
        while index < len(lines) and not lines[index].startswith(("@@ ", "--- ")):
            line = lines[index]
            if line.startswith("\\ No newline"):
                index += 1
                continue
            if not line or line[0] not in {" ", "+", "-"}:
                break
            marker, content = line[0], line[1:]
            if marker in {" ", "-"}:
                if old_cursor >= len(base) or base[old_cursor] != content:
                    raise DiffReconstructionError(
                        "DIFF_CONTEXT_MISMATCH", "Diff context does not match the supplied base file."
                    )
                old_cursor += 1
                consumed += 1
            if marker in {" ", "+"}:
                output.append(content)
            index += 1
        if consumed != old_count:
            raise DiffReconstructionError("INVALID_DIFF_HUNK", "Diff hunk old-line count does not match.")
    if not saw_hunk:
        raise DiffReconstructionError("INVALID_DIFF", "No unified-diff hunks were found.")
    output.extend(base[old_cursor:])
    return output, index


def reconstruct_unified_diff(
    diff: str,
    *,
    base_files: dict[str, str] | None = None,
) -> list[PatchedFile]:
    if not diff.strip():
        raise DiffReconstructionError("INVALID_DIFF", "Diff must not be empty.")
    base_files = base_files or {}
    lines = diff.splitlines()
    results: list[PatchedFile] = []
    index = 0
    while index < len(lines):
        if not lines[index].startswith("--- "):
            index += 1
            continue
        old_path = _header_path(lines[index][4:])
        index += 1
        if index >= len(lines) or not lines[index].startswith("+++ "):
            raise DiffReconstructionError("INVALID_DIFF", "A --- header must be followed by +++.")
        new_path = _header_path(lines[index][4:])
        index += 1
        if old_path is None:
            base: list[str] = []
        else:
            base_source = base_files.get(old_path)
            if base_source is None:
                base_source = base_files.get(new_path or "")
            if base_source is None:
                raise DiffReconstructionError(
                    "DIFF_CONTEXT_REQUIRED",
                    f"Base content is required for modified file {old_path}.",
                )
            base = base_source.splitlines()
        patched, index = _apply_hunks(lines, index, base)
        source = "\n".join(patched) + ("\n" if patched else "")
        results.append(
            PatchedFile(old_path=old_path, new_path=new_path, source=source, deleted=new_path is None)
        )
    if not results:
        raise DiffReconstructionError("INVALID_DIFF", "No file patches were found.")
    return results
