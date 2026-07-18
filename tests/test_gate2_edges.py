from __future__ import annotations

from pathlib import Path

import pytest

from archagent_audit.engine import scan_path


def scan_source(tmp_path: Path, source: str) -> set[str]:
    (tmp_path / "agent.py").write_text(source, encoding="utf-8")
    return {finding.rule_id for finding in scan_path(tmp_path).findings}


def test_constant_turn_limit_is_resolved(tmp_path: Path) -> None:
    ids = scan_source(
        tmp_path,
        "MAX_TURNS = 8\nresult = Runner.run(agent, task, max_turns=MAX_TURNS)\n",
    )
    assert "AA001" not in ids


@pytest.mark.parametrize(
    ("config", "found", "warning"),
    [
        ('{"recursion_limit": 20}', False, False),
        ('{"recursion_limit": None}', True, False),
        ('{"recursion_limit": settings.limit}', False, True),
    ],
)
def test_langgraph_recursion_limit(
    tmp_path: Path,
    config: str,
    found: bool,
    warning: bool,
) -> None:
    (tmp_path / "graph.py").write_text(
        f"result = graph.invoke(inputs, config={config})\n",
        encoding="utf-8",
    )
    report = scan_path(tmp_path)

    assert ("AA001" in {finding.rule_id for finding in report.findings}) is found
    assert ("AA001_INCONCLUSIVE_BOUND" in {item.code for item in report.analysis_warnings}) is warning


def test_direct_recursion_without_base_case_is_flagged(tmp_path: Path) -> None:
    ids = scan_source(tmp_path, "def run_agent():\n    return run_agent()\n")
    assert "AA001" in ids


def test_recursive_function_with_base_case_is_clean(tmp_path: Path) -> None:
    ids = scan_source(
        tmp_path,
        "def run_agent(turns):\n"
        "    if turns <= 0:\n"
        "        return 'done'\n"
        "    return run_agent(turns - 1)\n",
    )
    assert "AA001" not in ids


@pytest.mark.parametrize(
    ("body", "has_aa002"),
    [
        ('client.responses.create(model="gpt", input="x")', True),
        ('client.responses.create(model="gpt", input="x", max_output_tokens=100)', True),
        ('BUDGET=100\nif spent >= BUDGET: raise StopIteration\nclient.responses.create(model="gpt", input="x")', True),
        ('BUDGET=100\nif spent >= BUDGET: raise StopIteration\nclient.responses.create(model="gpt", input="x", max_output_tokens=100)', False),
    ],
)
def test_output_and_whole_run_budgets_are_independent(
    tmp_path: Path,
    body: str,
    has_aa002: bool,
) -> None:
    ids = scan_source(tmp_path, body + "\n")
    assert ("AA002" in ids) is has_aa002


def test_parameterized_sql_is_not_unvalidated(tmp_path: Path) -> None:
    ids = scan_source(
        tmp_path,
        "def lookup(user_id):\n"
        "    return cursor.execute('select * from users where id = ?', (user_id,))\n",
    )
    assert "AA004" not in ids


def test_interpolated_sql_is_unvalidated(tmp_path: Path) -> None:
    ids = scan_source(
        tmp_path,
        "def lookup(user_id):\n"
        "    return cursor.execute(f'select * from users where id = {user_id}')\n",
    )
    assert "AA004" in ids


def test_ambiguous_write_tool_is_deferred_to_judgment(tmp_path: Path) -> None:
    ids = scan_source(
        tmp_path,
        "@function_tool\n"
        "def process_record(value):\n"
        "    database.write(value)\n",
    )
    assert "AA003" not in ids


def test_environment_secret_alone_is_clean(tmp_path: Path) -> None:
    ids = scan_source(tmp_path, 'API_KEY = os.environ["OPENAI_API_KEY"]\n')
    assert "AA006" not in ids


def test_environment_secret_interpolated_into_prompt_is_flagged(tmp_path: Path) -> None:
    ids = scan_source(
        tmp_path,
        'API_KEY = os.environ["OPENAI_API_KEY"]\n'
        'client.responses.create(model="gpt", input=f"secret={API_KEY}", max_output_tokens=10)\n',
    )
    assert "AA006" in ids

