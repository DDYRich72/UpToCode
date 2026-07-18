"""Command-line interface for ArchAgent."""

from enum import StrEnum
from pathlib import Path

import typer

from archagent_audit.engine import scan_path
from archagent_audit.models import SEVERITY_ORDER, Severity
from archagent_audit.reporters.json import render_json

app = typer.Typer(
    name="archagent-audit",
    help="ArchAgent architecture-quality analysis for Python agent applications.",
    no_args_is_help=True,
)


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
    if output_format not in {OutputFormat.JSON, OutputFormat.TERMINAL}:
        typer.echo(f"{output_format.value} reporting is not implemented yet", err=True)
        raise typer.Exit(2)
    try:
        report = scan_path(path)
    except (OSError, ValueError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from error
    rendered = render_json(report)
    if output is not None:
        output.write_text(rendered, encoding="utf-8")
    else:
        typer.echo(rendered)
    if fail_on is not None and any(
        SEVERITY_ORDER[finding.severity] <= SEVERITY_ORDER[fail_on]
        for finding in report.findings
    ):
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
