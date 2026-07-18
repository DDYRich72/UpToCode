"""Command-line interface for ArchAgent."""

import typer

app = typer.Typer(
    name="archagent-audit",
    help="ArchAgent architecture-quality analysis for Python agent applications.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Run ArchAgent commands."""


if __name__ == "__main__":
    app()

