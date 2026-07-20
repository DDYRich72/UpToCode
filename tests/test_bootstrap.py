from typer.testing import CliRunner


def test_package_import_and_cli_help() -> None:
    from uptocode.cli import app

    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "UpToCode" in result.stdout

