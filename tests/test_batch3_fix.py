from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from typer.testing import CliRunner

from uptocode.cli import app
from uptocode.engine import scan_path
from uptocode.models import FixSession
from uptocode.review import create_manifest


runner = CliRunner()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    repo = tmp_path / "repo with spaces"
    repo.mkdir()
    (repo / ".gitignore").write_text(".uptocode/\n", encoding="utf-8")
    source = repo / "agent.py"
    source.write_text("while True:\n    work()\n", encoding="utf-8")
    helper = repo / "fake_runner.py"
    helper.write_text(
        """from pathlib import Path
import sys
target = Path(sys.argv[1])
mode = sys.argv[2]
if mode == 'fix':
    target.write_text(target.read_text().replace('while True:', 'for _ in range(1):'))
elif mode == 'fail':
    raise SystemExit(7)
""",
        encoding="utf-8",
    )
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "UpToCode Tests")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture")
    report = scan_path(repo)
    manifest = create_manifest(report, approve={report.findings[0].fingerprint})
    report_path = tmp_path / "report.json"
    manifest_path = tmp_path / "manifest.json"
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    template = f'"{sys.executable}" "{helper}" "{{file}}" fix "{{prompt_file}}"'
    return repo, report_path, manifest_path, template


def test_fix_dry_run_writes_nothing(tmp_path: Path) -> None:
    repo, report_path, manifest_path, template = _fixture(tmp_path)
    before_refs = _git(repo, "for-each-ref", "--format=%(refname)")
    before_status = _git(repo, "status", "--porcelain")

    result = runner.invoke(
        app,
        [
            "fix",
            str(report_path),
            "--manifest",
            str(manifest_path),
            "--runner",
            "command",
            "--command",
            template,
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output
    assert "uptocode/fix-" in result.output
    assert _git(repo, "for-each-ref", "--format=%(refname)") == before_refs
    assert _git(repo, "status", "--porcelain") == before_status
    assert not (repo / ".uptocode" / "fix-session.json").exists()


def test_fix_apply_uses_retained_worktree_and_strict_session(tmp_path: Path) -> None:
    repo, report_path, manifest_path, template = _fixture(tmp_path)
    result = runner.invoke(
        app,
        [
            "fix",
            str(report_path),
            "--manifest",
            str(manifest_path),
            "--runner",
            "command",
            "--command",
            template,
            "--verify-command",
            f'"{sys.executable}" -c "raise SystemExit(0)"',
            "--apply",
        ],
    )

    assert result.exit_code == 0, result.output
    session = FixSession.model_validate_json(
        (repo / ".uptocode" / "fix-session.json").read_text(encoding="utf-8")
    )
    assert session.results[0].status == "PASS"
    assert session.results[0].fingerprint_gone is True
    assert session.results[0].verification_status == "passed"
    worktree = Path(session.results[0].worktree)
    assert worktree.is_dir()
    assert "for _ in range(1)" in (worktree / "agent.py").read_text(encoding="utf-8")
    assert "while True" in (repo / "agent.py").read_text(encoding="utf-8")
    assert _git(repo, "status", "--porcelain") == ""


def test_fix_refuses_dirty_stale_and_invalid_runner(tmp_path: Path) -> None:
    repo, report_path, manifest_path, template = _fixture(tmp_path)
    (repo / "dirty.txt").write_text("dirty", encoding="utf-8")
    dirty = runner.invoke(
        app,
        [
            "fix",
            str(report_path),
            "--manifest",
            str(manifest_path),
            "--runner",
            "command",
            "--command",
            template,
            "--apply",
        ],
    )
    assert dirty.exit_code == 2
    assert "clean Git worktree" in dirty.output
    (repo / "dirty.txt").unlink()

    invalid = runner.invoke(
        app,
        [
            "fix",
            str(report_path),
            "--manifest",
            str(manifest_path),
            "--runner",
            "command",
            "--command",
            f'"{sys.executable}" -V',
        ],
    )
    assert invalid.exit_code == 2
    assert "{prompt_file}" in invalid.output

    (repo / "agent.py").write_text("print('already fixed')\n", encoding="utf-8")
    stale = runner.invoke(
        app,
        [
            "fix",
            str(report_path),
            "--manifest",
            str(manifest_path),
            "--runner",
            "command",
            "--command",
            template,
        ],
    )
    assert stale.exit_code == 2
    assert "stale" in stale.output.lower()


def test_fix_failure_retains_branch_and_worktree(tmp_path: Path) -> None:
    repo, report_path, manifest_path, template = _fixture(tmp_path)
    failing = template.replace(" fix ", " fail ")
    result = runner.invoke(
        app,
        [
            "fix",
            str(report_path),
            "--manifest",
            str(manifest_path),
            "--runner",
            "command",
            "--command",
            failing,
            "--apply",
        ],
    )

    assert result.exit_code == 1, result.output
    session = FixSession.model_validate_json(
        (repo / ".uptocode" / "fix-session.json").read_text(encoding="utf-8")
    )
    item = session.results[0]
    assert item.status == "FAIL"
    assert item.runner_exit == 7
    assert Path(item.worktree).is_dir()
    assert _git(repo, "show-ref", "--verify", f"refs/heads/{item.branch}")
