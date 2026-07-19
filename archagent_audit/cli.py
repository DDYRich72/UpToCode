"""Command-line interface for ArchAgent."""

from enum import StrEnum
from pathlib import Path

import typer

from archagent_audit.engine import scan_path
from archagent_audit.models import SEVERITY_ORDER, Severity
from archagent_audit.models import Report, ReviewManifest
from archagent_audit.planner import generate_fixplan
from archagent_audit.reporters.json import render_json
from archagent_audit.reporters.html import render_html
from archagent_audit.reporters.terminal import render_terminal
from archagent_audit.review import create_manifest

app = typer.Typer(
    name="archagent-audit",
    help="ArchAgent architecture-quality analysis for Python agent applications.",
    no_args_is_help=True,
)


def _write_output(path: Path, content: str, *, create_parent: bool = False) -> None:
    try:
        if create_parent:
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as error:
        typer.echo(f"Could not write output {path}: {error}", err=True)
        raise typer.Exit(2) from error


@app.callback()
def main() -> None:
    """Run ArchAgent commands."""


class OutputFormat(StrEnum):
    TERMINAL = "terminal"
    JSON = "json"
    HTML = "html"
    GITHUB = "github"


@app.command()
def scan(
    path: Path,
    output_format: OutputFormat = typer.Option(
        OutputFormat.TERMINAL,
        "--format",
    ),
    output: Path | None = typer.Option(None, "--output"),
    judgment: bool = typer.Option(False, "--judgment"),
    send_code: bool = typer.Option(False, "--send-code"),
    fail_on: Severity | None = typer.Option(None, "--fail-on"),
) -> None:
    """Scan a Python repository for architecture-quality findings."""
    if judgment and not send_code:
        typer.echo("--judgment requires --send-code consent", err=True)
        raise typer.Exit(2)
    if output_format == OutputFormat.HTML and output is None:
        typer.echo("--format html requires --output", err=True)
        raise typer.Exit(2)
    if output_format == OutputFormat.GITHUB:
        typer.echo(f"{output_format.value} reporting is not implemented yet", err=True)
        raise typer.Exit(2)
    try:
        report = scan_path(
            path,
            judgment=judgment,
            send_code=send_code,
        )
    except (OSError, ValueError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from error
    if report.coverage.files_discovered and not report.coverage.files_analyzed:
        typer.echo("No discovered Python file could be analyzed", err=True)
        raise typer.Exit(2)
    if output_format == OutputFormat.JSON:
        rendered = render_json(report)
    elif output_format == OutputFormat.HTML:
        rendered = render_html(report)
    else:
        rendered = render_terminal(report)
    if output is not None:
        _write_output(output, rendered)
    else:
        typer.echo(rendered)
    if fail_on is not None and any(
        SEVERITY_ORDER[finding.severity] <= SEVERITY_ORDER[fail_on]
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
) -> None:
    """Record approval and rejection decisions for an existing report."""
    report = _read_report(report_path)
    approve_set = _selectors(approve)
    reject_set = _selectors(reject)
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
    output = report_path.parent / ".archagent-audit" / "manifest.json"
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
def serve() -> None:
    """Serve the five ArchAgent tools over MCP stdio."""
    from archagent_audit.mcp_server import run_server

    run_server()


if __name__ == "__main__":
    app()
