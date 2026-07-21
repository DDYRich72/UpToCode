from __future__ import annotations

from pathlib import Path

import pytest

from uptocode.engine import scan_path
from uptocode.judgment_candidates import collect_judgment_candidates
from uptocode.rules.registry import core_rule_map


ROOT = Path(__file__).parents[1]
RULES = {"AA014", "AA015", "AA016", "AA017", "AA018"}


def _rule_ids(path: Path) -> set[str]:
    return {finding.rule_id for finding in scan_path(path).findings}


def test_bad_and_clean_mcp_fixtures() -> None:
    assert RULES <= _rule_ids(ROOT / "fixtures" / "bad_mcp_server")
    clean = scan_path(ROOT / "fixtures" / "clean_mcp_server")
    assert not (RULES & {finding.rule_id for finding in clean.findings})
    assert not [warning for warning in clean.analysis_warnings if warning.code.startswith("AA01")]


def test_stdio_is_not_applicable(tmp_path: Path) -> None:
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('local')\n"
        "mcp.run(transport='stdio')\n",
        encoding="utf-8",
    )
    assert "AA014" not in _rule_ids(tmp_path)


@pytest.mark.parametrize("rule_id", sorted(RULES))
def test_new_rule_suppressions(rule_id: str, tmp_path: Path) -> None:
    source = (ROOT / "fixtures" / "bad_mcp_server" / "server.py").read_text(
        encoding="utf-8"
    )
    report = scan_path(ROOT / "fixtures" / "bad_mcp_server")
    finding = next(item for item in report.findings if item.rule_id == rule_id)
    lines = source.splitlines()
    lines[finding.line - 1] += f"  # uptocode: ignore {rule_id}"
    (tmp_path / "server.py").write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert rule_id not in _rule_ids(tmp_path)


def test_dynamic_mcp_composition_produces_coverage_warnings(tmp_path: Path) -> None:
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('dynamic')\n"
        "transport = choose_transport()\n"
        "annotations = choose_annotations()\n"
        "@mcp.tool(annotations=annotations)\n"
        "def lookup(payload: UnknownArgs): return payload\n"
        "mcp.run(transport=transport)\n",
        encoding="utf-8",
    )
    codes = {warning.code for warning in scan_path(tmp_path).analysis_warnings}
    assert {
        "AA014_INCONCLUSIVE_MCP_TRANSPORT",
        "AA015_INCONCLUSIVE_TOOL_ANNOTATIONS",
    } <= codes


def test_mcp_names_without_registration_are_not_evidence(tmp_path: Path) -> None:
    (tmp_path / "plain.py").write_text(
        "def tool(annotations=None):\n    return 'Operation failed'\n",
        encoding="utf-8",
    )
    assert not (RULES & _rule_ids(tmp_path))


def test_experimental_judgment_candidates_are_nominated() -> None:
    source = """from mcp.server.fastmcp import FastMCP
mcp = FastMCP('x')
@mcp.tool()
def send_payment(amount):
    try:
        provider.send(amount)
    except ProviderError as exc:
        return render_error(exc)
policy = 'Only after identity confirmation may you send a payment.'
"""
    ids = {
        item.rule_id
        for item in collect_judgment_candidates([("server.py", source)])
    }
    assert {"AA017", "AA018"} <= ids


def test_registry_contract_for_new_rules() -> None:
    registry = core_rule_map()
    assert registry["AA014"].severity == "critical"
    assert registry["AA014"].maturity == "stable"
    assert registry["AA015"].maturity == "stable"
    assert registry["AA016"].maturity == "stable"
    assert registry["AA017"].maturity == "experimental"
    assert registry["AA018"].maturity == "experimental"
    assert all(registry[rule_id].citations for rule_id in RULES)
