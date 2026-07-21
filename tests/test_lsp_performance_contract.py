from pathlib import Path

from uptocode.engine import AuditService


def test_lsp_fixture_is_representative_and_scan_is_file_scoped() -> None:
    fixture = Path("fixtures/lsp/typical_agent.py")
    line_count = len(fixture.read_text(encoding="utf-8").splitlines())
    assert 300 <= line_count <= 500

    report = AuditService().scan(fixture)
    assert report.coverage.files_discovered == 1
    assert report.coverage.files_analyzed == 1
    assert {finding.file for finding in report.findings} <= {fixture.name}
