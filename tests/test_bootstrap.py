from typer.testing import CliRunner


def test_package_import_and_cli_help() -> None:
    from archagent_audit.cli import app

    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "ArchAgent" in result.stdout

