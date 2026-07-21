"""Approval-bound external remediation in retained isolated Git worktrees."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from string import Formatter
from typing import Literal
import os
import shlex
import subprocess
import tempfile

from uptocode.engine import scan_path
from uptocode.models import Finding, FixResult, FixSession, Report, ReviewManifest
from uptocode.planner import remediation_prompt
from uptocode.review import report_fingerprint


class FixRunner(StrEnum):
    CODEX = "codex"
    COMMAND = "command"


class FixPreflightError(ValueError):
    """A session-level failure that must occur before any branch is created."""


_PLACEHOLDERS = {"prompt_file", "file", "rule_id", "fingerprint"}


def _run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=check,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise FixPreflightError(f"Git command failed: {' '.join(args)}: {error}") from error


def parse_argv(value: str, *, placeholders: bool = False) -> list[str]:
    try:
        parts = shlex.split(value, posix=os.name != "nt")
    except ValueError as error:
        raise FixPreflightError(f"Invalid quoted command: {error}") from error
    if os.name == "nt":
        parts = [
            item[1:-1]
            if len(item) >= 2 and item[0] == item[-1] and item[0] in {'"', "'"}
            else item
            for item in parts
        ]
    if not parts:
        raise FixPreflightError("Command must contain at least one argument")
    if placeholders:
        fields = {
            field_name
            for part in parts
            for _, field_name, _, _ in Formatter().parse(part)
            if field_name is not None
        }
        unknown = fields - _PLACEHOLDERS
        if unknown:
            raise FixPreflightError(
                f"Unknown command placeholders: {', '.join(sorted(unknown))}"
            )
        if "prompt_file" not in fields:
            raise FixPreflightError("Custom runner command requires {prompt_file}")
    return parts


def _approved_findings(report: Report, manifest: ReviewManifest) -> list[Finding]:
    if manifest.report_fingerprint != report_fingerprint(report):
        raise FixPreflightError("Review manifest does not match this report")
    approved = {
        decision.fingerprint
        for decision in manifest.decisions
        if decision.status == "approved"
    }
    return [finding for finding in report.findings if finding.fingerprint in approved]


def _repository(scan_root: Path) -> Path:
    result = _run_git(scan_root, "rev-parse", "--show-toplevel")
    root = Path(result.stdout.strip()).resolve()
    try:
        scan_root.relative_to(root)
    except ValueError as error:
        raise FixPreflightError("Report scan root is outside its Git repository") from error
    return root


def _branch_and_worktree(repo: Path, finding: Finding) -> tuple[str, Path]:
    short = finding.fingerprint[:12]
    branch = f"uptocode/fix-{short}"
    worktree = repo.parent / ".uptocode-fix-worktrees" / f"{repo.name}-{short}"
    return branch, worktree


def _substitute(parts: list[str], finding: Finding, prompt_file: str) -> list[str]:
    values = {
        "prompt_file": prompt_file,
        "file": finding.file,
        "rule_id": finding.rule_id,
        "fingerprint": finding.fingerprint,
    }
    try:
        return [part.format_map(values) for part in parts]
    except (KeyError, ValueError) as error:
        raise FixPreflightError(f"Invalid command template: {error}") from error


def _runner_argv(
    runner: FixRunner,
    command_parts: list[str] | None,
    finding: Finding,
    prompt_file: str,
) -> list[str]:
    if runner == FixRunner.CODEX:
        return ["codex", "exec", "--ephemeral", "--sandbox", "workspace-write", "-"]
    assert command_parts is not None
    return _substitute(command_parts, finding, prompt_file)


def _validate_session(
    report: Report,
    manifest: ReviewManifest,
    runner: FixRunner,
    command: str | None,
    verify_command: str | None,
    *,
    apply: bool,
) -> tuple[Path, Path, str, list[Finding], list[str] | None, list[str] | None]:
    if report.scan_root.startswith("<"):
        raise FixPreflightError("A share-safe or unresolved scan root cannot be fixed")
    scan_root = Path(report.scan_root).expanduser().resolve()
    if not scan_root.is_dir():
        raise FixPreflightError(f"Report scan root is not a directory: {scan_root}")
    repo = _repository(scan_root)
    findings = _approved_findings(report, manifest)
    if runner == FixRunner.CODEX and command is not None:
        raise FixPreflightError("--command is valid only with --runner command")
    if runner == FixRunner.COMMAND and command is None:
        raise FixPreflightError("--runner command requires --command")
    command_parts = parse_argv(command, placeholders=True) if command is not None else None
    verify_parts = parse_argv(verify_command) if verify_command is not None else None
    base_revision = _run_git(repo, "rev-parse", "HEAD").stdout.strip()
    fresh = scan_path(scan_root)
    available = {finding.fingerprint for finding in fresh.findings}
    stale = [finding.fingerprint for finding in findings if finding.fingerprint not in available]
    if stale:
        raise FixPreflightError(f"Approved findings are stale: {', '.join(stale)}")
    if apply and _run_git(repo, "status", "--porcelain").stdout.strip():
        raise FixPreflightError("fix --apply requires a clean Git worktree")
    for finding in findings:
        branch, worktree = _branch_and_worktree(repo, finding)
        branch_exists = _run_git(
            repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False
        ).returncode == 0
        if branch_exists:
            raise FixPreflightError(f"Fix branch already exists: {branch}")
        if worktree.exists():
            raise FixPreflightError(f"Fix worktree path already exists: {worktree}")
    return repo, scan_root, base_revision, findings, command_parts, verify_parts


def render_dry_run(
    report: Report,
    manifest: ReviewManifest,
    runner: FixRunner,
    command: str | None,
    verify_command: str | None,
) -> str:
    repo, scan_root, base, findings, command_parts, verify_parts = _validate_session(
        report, manifest, runner, command, verify_command, apply=False
    )
    lines = [f"Dry run from {base}", f"Repository: {repo}"]
    if not findings:
        lines.append("No approved findings.")
    for finding in findings:
        branch, worktree = _branch_and_worktree(repo, finding)
        argv = _runner_argv(runner, command_parts, finding, "<temporary-prompt-file>")
        lines.extend(
            [
                "",
                f"{finding.rule_id} {finding.fingerprint}",
                f"  branch: {branch}",
                f"  worktree: {worktree}",
                f"  runner: {subprocess.list2cmdline(argv)}",
                f"  rescan: {worktree / scan_root.relative_to(repo)}",
                "  verify: "
                + (subprocess.list2cmdline(verify_parts) if verify_parts else "not requested"),
            ]
        )
    return "\n".join(lines)


def apply_fixes(
    report: Report,
    manifest: ReviewManifest,
    runner: FixRunner,
    command: str | None,
    verify_command: str | None,
) -> FixSession:
    repo, scan_root, base, findings, command_parts, verify_parts = _validate_session(
        report, manifest, runner, command, verify_command, apply=True
    )
    scan_relative = scan_root.relative_to(repo)
    results: list[FixResult] = []
    for finding in findings:
        branch, worktree = _branch_and_worktree(repo, finding)
        runner_exit: int | None = None
        fingerprint_gone: bool | None = None
        verification_status: Literal["not_requested", "not_run", "passed", "failed"] = (
            "not_requested" if verify_parts is None else "not_run"
        )
        verification_exit: int | None = None
        reason: str | None = None
        prompt_path: Path | None = None
        try:
            worktree.parent.mkdir(parents=True, exist_ok=True)
            _run_git(repo, "worktree", "add", "-b", branch, str(worktree), base)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", suffix=".md", delete=False
            ) as prompt_stream:
                prompt_stream.write(remediation_prompt(finding))
                prompt_path = Path(prompt_stream.name)
            argv = _runner_argv(runner, command_parts, finding, str(prompt_path))
            prompt = remediation_prompt(finding) if runner == FixRunner.CODEX else None
            completed = subprocess.run(
                argv,
                cwd=worktree,
                input=prompt,
                text=True,
                encoding="utf-8",
                timeout=None,
                check=False,
            )
            runner_exit = completed.returncode
            if runner_exit != 0:
                reason = f"Runner exited {runner_exit}"
            else:
                verified_report = scan_path(worktree / scan_relative)
                fingerprint_gone = finding.fingerprint not in {
                    item.fingerprint for item in verified_report.findings
                }
                if not fingerprint_gone:
                    reason = "Finding fingerprint remains after runner completion"
                elif verify_parts is not None:
                    verification = subprocess.run(
                        verify_parts,
                        cwd=worktree,
                        text=True,
                        encoding="utf-8",
                        timeout=None,
                        check=False,
                    )
                    verification_exit = verification.returncode
                    verification_status = (
                        "passed" if verification.returncode == 0 else "failed"
                    )
                    if verification.returncode != 0:
                        reason = f"Verification command exited {verification.returncode}"
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            reason = str(error)
        finally:
            if prompt_path is not None:
                prompt_path.unlink(missing_ok=True)
        passed = (
            runner_exit == 0
            and fingerprint_gone is True
            and verification_status in {"not_requested", "passed"}
        )
        results.append(
            FixResult(
                rule_id=finding.rule_id,
                fingerprint=finding.fingerprint,
                file=finding.file,
                branch=branch,
                worktree=str(worktree),
                runner_exit=runner_exit,
                fingerprint_gone=fingerprint_gone,
                verification_status=verification_status,
                verification_exit=verification_exit,
                status="PASS" if passed else "FAIL",
                reason=None if passed else reason or "Remediation did not pass verification",
            )
        )
    return FixSession(
        report_fingerprint=report_fingerprint(report),
        base_revision=base,
        results=results,
    )


def render_fix_session(session: FixSession) -> str:
    lines = ["STATUS  RULE   FINGERPRINT                   BRANCH"]
    for result in session.results:
        lines.append(
            f"{result.status:<6}  {result.rule_id:<5}  {result.fingerprint:<28}  {result.branch}"
        )
        if result.reason:
            lines.append(f"        reason: {result.reason}")
    if not session.results:
        lines.append("No approved findings.")
    return "\n".join(lines)
