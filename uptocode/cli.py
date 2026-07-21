"""Command-line interface for UpToCode."""

from enum import StrEnum
import os
import subprocess
from pathlib import Path

import typer

from uptocode import __version__
from uptocode.baseline import Baseline, apply_baseline, create_baseline, load_baseline
from uptocode.engine import scan_path
from uptocode.models import SEVERITY_ORDER, Severity
from uptocode.models import Report, ReviewManifest
from uptocode.planner import generate_fixplan
from uptocode.reporters.json import render_json
from uptocode.reporters.html import render_html
from uptocode.reporters.github import render_github, render_github_summary
from uptocode.reporters.terminal import render_terminal
from uptocode.reporters.sarif import render_sarif
from uptocode.review import create_manifest
from uptocode.share_safe import make_share_safe

app = typer.Typer(
    name="uptocode",
    help="UpToCode architecture-quality analysis for Python and TypeScript agent applications.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


def _write_output(path: Path, content: str, *, create_parent: bool = False) -> None:
    try:
        if create_parent:
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as error:
        typer.echo(f"Could not write output {path}: {error}", err=True)
        raise typer.Exit(2) from error


def _append_output(path: Path, content: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
    except OSError as error:
        typer.echo(f"Could not append GitHub summary {path}: {error}", err=True)
        raise typer.Exit(2) from error


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the UpToCode version and exit.",
    ),
) -> None:
    """Run UpToCode commands."""


class OutputFormat(StrEnum):
    TERMINAL = "terminal"
    JSON = "json"
    HTML = "html"
    GITHUB = "github"
    SARIF = "sarif"


@app.command()
def scan(
    path: Path,
    output_format: OutputFormat = typer.Option(
        OutputFormat.TERMINAL,
        "--format",
    ),
    output: Path | None = typer.Option(None, "--output"),
    json_output: Path | None = typer.Option(
        None,
        "--json-output",
        help="Also write the exact Report JSON used by another output format.",
    ),
    judgment: bool = typer.Option(False, "--judgment"),
    send_code: bool = typer.Option(False, "--send-code"),
    fail_on: Severity | None = typer.Option(None, "--fail-on"),
    include_experimental: bool = typer.Option(False, "--include-experimental"),
    share_safe: bool = typer.Option(False, "--share-safe"),
    baseline: Path | None = typer.Option(None, "--baseline"),
    update_baseline: Path | None = typer.Option(None, "--update-baseline"),
    changed_since: str | None = typer.Option(None, "--changed-since"),
    select: str | None = typer.Option(None, "--select"),
    ignore: str | None = typer.Option(None, "--ignore"),
    exclude: list[str] | None = typer.Option(None, "--exclude"),
    severity: list[str] | None = typer.Option(None, "--severity", metavar="RULE=LEVEL"),
    fail_on_analysis_warning: bool = typer.Option(False, "--fail-on-analysis-warning"),
    github_summary: Path | None = typer.Option(None, "--github-summary"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Scan supported source files for architecture-quality findings."""
    if judgment and not send_code:
        typer.echo("--judgment requires --send-code consent", err=True)
        raise typer.Exit(2)
    if output_format == OutputFormat.HTML and output is None:
        typer.echo("--format html requires --output", err=True)
        raise typer.Exit(2)
    if share_safe and output_format not in {OutputFormat.JSON, OutputFormat.HTML, OutputFormat.SARIF}:
        typer.echo("--share-safe requires --format json, html, or sarif", err=True)
        raise typer.Exit(2)
    severity_overrides: dict[str, str] = {}
    for value in severity or []:
        rule_id, separator, level = value.partition("=")
        if not separator or level not in {item.value for item in Severity}:
            typer.echo(f"Invalid --severity {value!r}; use RULE=critical|warning|info", err=True)
            raise typer.Exit(2)
        severity_overrides[rule_id.upper()] = level
    try:
        report = scan_path(
            path,
            judgment=judgment,
            send_code=send_code,
            extra_excludes=exclude,
            severity_overrides=severity_overrides,
        )
    except (OSError, ValueError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from error
    if (report.coverage.files_discovered or report.coverage.files_skipped) and not report.coverage.files_analyzed:
        typer.echo("No discovered supported source file could be analyzed", err=True)
        raise typer.Exit(2)
    selected = _selectors(select)
    ignored = _selectors(ignore)
    if selected:
        report.findings = [item for item in report.findings if item.rule_id in selected]
    if ignored:
        report.findings = [item for item in report.findings if item.rule_id not in ignored]
    if changed_since:
        try:
            changed = subprocess.run(
                [
                    "git",
                    "diff",
                    "--name-only",
                    f"{changed_since}...HEAD",
                    "--",
                    "*.py",
                    "*.ts",
                    "*.tsx",
                    "*.mts",
                ],
                cwd=path if path.is_dir() else path.parent,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=10,
                check=True,
            )
        except (OSError, subprocess.SubprocessError) as error:
            typer.echo(f"Could not resolve --changed-since: {error}", err=True)
            raise typer.Exit(2) from error
        changed_files = {item.replace("\\", "/") for item in changed.stdout.splitlines()}
        report.findings = [item for item in report.findings if item.file in changed_files]
        report.analysis_warnings = [
            item for item in report.analysis_warnings if item.file is None or item.file in changed_files
        ]
    scanned_findings = list(report.findings)
    baseline_data: Baseline | None = None
    if baseline is not None:
        try:
            baseline_data = load_baseline(baseline.read_text(encoding="utf-8"))
            report, _ = apply_baseline(report, baseline_data, findings=scanned_findings)
        except (OSError, ValueError) as error:
            typer.echo(f"Invalid baseline {baseline}: {error}", err=True)
            raise typer.Exit(2) from error
    if update_baseline is not None:
        try:
            if baseline_data is None and update_baseline.exists():
                baseline_data = load_baseline(update_baseline.read_text(encoding="utf-8"))
                report, _ = apply_baseline(
                    report,
                    baseline_data,
                    findings=scanned_findings,
                    mute=False,
                )
        except (OSError, ValueError) as error:
            typer.echo(f"Invalid baseline {update_baseline}: {error}", err=True)
            raise typer.Exit(2) from error
        updated = create_baseline(
            report,
            previous=baseline_data,
            findings=scanned_findings,
        )
        _write_output(update_baseline, updated.model_dump_json(indent=2), create_parent=True)
    rendered_report = make_share_safe(report) if share_safe else report
    if output_format == OutputFormat.JSON:
        rendered = render_json(rendered_report)
    elif output_format == OutputFormat.HTML:
        rendered = render_html(rendered_report)
    elif output_format == OutputFormat.SARIF:
        rendered = render_sarif(rendered_report)
    elif output_format == OutputFormat.GITHUB:
        rendered = render_github(rendered_report)
    else:
        rendered = render_terminal(rendered_report)
    if output is not None:
        _write_output(output, rendered)
    else:
        typer.echo(rendered)
    if json_output is not None:
        _write_output(json_output, render_json(rendered_report), create_parent=True)
    summary_destination = github_summary
    if summary_destination is None and os.environ.get("GITHUB_STEP_SUMMARY"):
        summary_destination = Path(os.environ["GITHUB_STEP_SUMMARY"])
    if summary_destination is not None:
        _append_output(summary_destination, render_github_summary(report))
    if verbose and report.metadata is not None:
        typer.echo(f"Scan duration: {report.metadata.duration_ms} ms", err=True)
    if fail_on_analysis_warning and report.analysis_warnings:
        raise typer.Exit(1)
    if fail_on is not None and any(
        SEVERITY_ORDER[finding.severity] <= SEVERITY_ORDER[fail_on]
        and (finding.maturity == "stable" or include_experimental)
        for finding in report.findings
    ):
        raise typer.Exit(1)


def _read_report(path: Path) -> Report:
    try:
        return Report.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise typer.BadParameter(f"Invalid report: {path}") from error


def _selectors(value: str | None) -> set[str]:
    return {item.strip() for item in (value or "").split(",") if item.strip()}


@app.command("review")
def review_command(
    report_path: Path = typer.Argument(..., metavar="REPORT"),
    approve: str | None = typer.Option(None, "--approve"),
    approve_all: bool = typer.Option(False, "--approve-all"),
    reject: str | None = typer.Option(None, "--reject"),
    non_interactive: bool = typer.Option(False, "--non-interactive"),
    reuse: Path | None = typer.Option(None, "--reuse"),
) -> None:
    """Record approval and rejection decisions for an existing report."""
    report = _read_report(report_path)
    approve_set = _selectors(approve)
    reject_set = _selectors(reject)
    if reuse is not None:
        try:
            prior = ReviewManifest.model_validate_json(reuse.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            typer.echo(f"Invalid reuse manifest {reuse}: {error}", err=True)
            raise typer.Exit(2) from error
        available = {finding.fingerprint for finding in report.findings}
        unmatched = []
        for decision in prior.decisions:
            if decision.fingerprint not in available:
                unmatched.append(decision.fingerprint)
            elif decision.status == "approved":
                approve_set.add(decision.fingerprint)
            else:
                reject_set.add(decision.fingerprint)
        if unmatched:
            typer.echo(f"Unmatched reused decisions: {', '.join(sorted(unmatched))}", err=True)
    if non_interactive and not (approve_all or approve_set or reject_set):
        typer.echo("Non-interactive review requires at least one decision", err=True)
        raise typer.Exit(2)
    if not non_interactive and not (approve_all or approve_set or reject_set):
        for finding in report.findings:
            if typer.confirm(
                f"Approve {finding.rule_id} {finding.file}:{finding.line}?",
                default=False,
            ):
                approve_set.add(finding.fingerprint)
            else:
                reject_set.add(finding.fingerprint)
    try:
        manifest = create_manifest(
            report,
            approve=approve_set,
            reject=reject_set,
            approve_all=approve_all,
        )
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from error
    output = report_path.parent / ".uptocode" / "manifest.json"
    _write_output(output, manifest.model_dump_json(indent=2), create_parent=True)
    typer.echo(str(output))


@app.command("plan")
def plan_command(
    report_path: Path = typer.Argument(..., metavar="REPORT"),
    manifest_path: Path = typer.Option(..., "--manifest", metavar="MANIFEST"),
    output: Path = typer.Option(Path("FIXPLAN.md"), "--output"),
) -> None:
    """Generate a non-mutating Codex plan for approved findings."""
    report = _read_report(report_path)
    try:
        manifest = ReviewManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        rendered = generate_fixplan(report, manifest)
    except (OSError, ValueError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from error
    _write_output(output, rendered)
    typer.echo(str(output))


@app.command()
def serve(
    transport: str = typer.Option("stdio", "--transport"),
    root: Path | None = typer.Option(None, "--root"),
    mode: str = typer.Option("local", "--mode"),
) -> None:
    """Serve the typed UpToCode catalog over local stdio or hosted HTTP."""
    from uptocode.mcp_server import run_server

    run_server(transport=transport, root=root, mode=mode)


if __name__ == "__main__":
    app()
