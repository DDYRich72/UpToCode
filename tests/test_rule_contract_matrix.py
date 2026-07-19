from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from archagent_audit.engine import scan_path
from archagent_audit.judgment import JudgmentBatch, JudgmentFinding


class FakeResponses:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def parse(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, response: object) -> None:
        self.responses = FakeResponses(response)


def sent_rule_ids(client: FakeClient) -> set[str]:
    ids: set[str] = set()
    for call in client.responses.calls:
        messages = call["input"]
        payload = json.loads(messages[1]["content"])
        ids.update(item["rule_id"] for item in payload)
    return ids


STATIC_SUPPRESSIONS = [
    ("AA001", "# archagent-audit: ignore AA001\nwhile True:\n    work()\n"),
    ("AA002", '# archagent-audit: ignore AA002\nclient.responses.create(model="gpt", input="x")\n'),
    ("AA003", "@function_tool  # archagent-audit: ignore AA003\ndef delete_user(value):\n    database.delete(value)\n"),
    ("AA004", "@function_tool  # archagent-audit: ignore AA004\ndef tool(model_arg):\n    subprocess.run(model_arg)\n"),
    ("AA006", '# archagent-audit: ignore AA006\nKEY="sk-proj-abcdefghijklmnopqrstuvwxyz123456"\n'),
    ("AA007", '# archagent-audit: ignore AA007\nclient.responses.create(model="gpt", input="x")\n'),
    ("AA010", "# archagent-audit: ignore AA010\nsave(response.output_text)\n"),
    ("AA011", '# archagent-audit: ignore AA011\nagent = Agent(name="x")\n'),
    ("AA012", '# archagent-audit: ignore AA012\nagent = Agent(name="x")\n'),
]


@pytest.mark.parametrize(("rule_id", "source"), STATIC_SUPPRESSIONS)
def test_every_static_rule_honors_location_suppression(
    tmp_path: Path,
    rule_id: str,
    source: str,
) -> None:
    (tmp_path / "agent.py").write_text(source, encoding="utf-8")

    report = scan_path(tmp_path)

    assert rule_id not in {item.rule_id for item in report.findings}
    assert report.suppressions >= 1


CLEAN_REGRESSIONS = [
    ("AA001", "result = Runner.run(agent, task, max_turns=10)\n"),
    ("AA002", 'BUDGET=100\nif spent >= BUDGET: raise StopIteration\nclient.responses.create(model="gpt", input="x", max_output_tokens=10)\n'),
    ("AA003", "@function_tool(needs_approval=True)\ndef delete_user(value):\n    database.delete(value)\n"),
    ("AA004", "@function_tool\ndef lookup(user_id):\n    cursor.execute('select * from t where id=?', (user_id,))\n"),
    ("AA006", 'KEY = os.environ["OPENAI_API_KEY"]\n'),
    ("AA007", 'client = OpenAI(timeout=30, max_retries=2)\nclient.responses.create(model="gpt", input="x")\n'),
    ("AA010", 'save(SafeResult.model_validate({"text": response.output_text}))\n'),
    ("AA011", 'agent = Agent(name="x")\n# archagent-audit: eval agent\n'),
    ("AA012", 'logger.info("start")\nagent = Agent(name="x")\n'),
]


@pytest.mark.parametrize(("rule_id", "source"), CLEAN_REGRESSIONS)
def test_every_static_rule_has_a_false_positive_regression(
    tmp_path: Path,
    rule_id: str,
    source: str,
) -> None:
    (tmp_path / "agent.py").write_text(source, encoding="utf-8")

    report = scan_path(tmp_path)

    assert rule_id not in {item.rule_id for item in report.findings}


@pytest.mark.parametrize("rule_id", [f"AA{number:03d}" for number in range(1, 13)])
def test_dynamic_unsupported_agent_syntax_never_reports_silent_clean(
    tmp_path: Path,
    rule_id: str,
) -> None:
    (tmp_path / f"{rule_id.lower()}.py").write_text(
        'runner = getattr(Runner, "run")\nresult = runner(agent, task)\n',
        encoding="utf-8",
    )

    report = scan_path(tmp_path)

    assert "UNSUPPORTED_DYNAMIC_AGENT_SYNTAX" in {
        item.code for item in report.analysis_warnings
    }


JUDGMENT_RULES = {
    "AA003": "https://openai.github.io/openai-agents-python/human_in_the_loop/",
    "AA005": "https://developers.openai.com/api/docs/guides/agent-builder-safety",
    "AA008": "https://www.anthropic.com/engineering/building-effective-agents",
    "AA009": "https://developers.openai.com/api/docs/guides/function-calling",
    "AA010": "https://developers.openai.com/api/docs/guides/function-calling",
    "AA011": "https://developers.openai.com/api/docs/guides/evals",
}


@pytest.mark.parametrize(("rule_id", "citation"), JUDGMENT_RULES.items())
def test_every_judgment_rule_accepts_a_schema_valid_positive(
    tmp_path: Path,
    rule_id: str,
    citation: str,
) -> None:
    sources = {
        "AA003": "@function_tool\ndef process_record(value):\n    database.write(value)\n",
        "AA005": 'external = requests.get(url)\nclient.responses.create(model="gpt", input=external)\n',
        "AA008": 'first = Agent(name="one")\nsecond = Agent(name="two")\n',
        "AA009": "@function_tool\ndef act(value):\n    return value\n",
        "AA010": "save_result(response.output_text)\n",
        "AA011": 'agent = Agent(name="one")\n',
    }
    source = sources[rule_id]
    (tmp_path / "agent.py").write_text(source, encoding="utf-8")
    line = {
        "AA003": 2,
        "AA005": 2,
        "AA008": 1,
        "AA009": 2,
        "AA010": 1,
        "AA011": 1,
    }[rule_id]
    parsed = JudgmentBatch(
        findings=[
            JudgmentFinding(
                rule_id=rule_id,
                file="agent.py",
                line=line,
                title=f"{rule_id} judgment finding",
                severity="warning" if rule_id not in {"AA003", "AA005"} else "critical",
                observed="Candidate evidence supports this architecture concern.",
                implies="The design may fail under realistic use.",
                recommended="Apply the rule-specific architecture control.",
                tradeoff="The control adds bounded implementation cost.",
                citation_url=citation,
            )
        ]
    )
    client = FakeClient(SimpleNamespace(output_parsed=parsed, output=[]))

    report = scan_path(
        tmp_path,
        judgment=True,
        send_code=True,
        judgment_client=client,
    )

    assert rule_id in sent_rule_ids(client)
    if rule_id in {"AA010", "AA011"}:
        # Static evidence owns the single finding at this location; judgment is
        # still exercised but cannot duplicate the actionable defect.
        assert any(item.rule_id == rule_id for item in report.findings)
    else:
        assert any(
            item.rule_id == rule_id and item.tier == "judgment"
            for item in report.findings
        )


JUDGMENT_SUPPRESSIONS = {
    "AA003": "@function_tool  # archagent-audit: ignore AA003\ndef process_record(value):\n    database.write(value)\n",
    "AA005": 'external = requests.get(url)\n# archagent-audit: ignore AA005\nclient.responses.create(model="gpt", input=external)\n',
    "AA008": '# archagent-audit: ignore AA008\nfirst = Agent(name="one")\nsecond = Agent(name="two")\n',
    "AA009": "@function_tool  # archagent-audit: ignore AA009\ndef act(value):\n    return value\n",
    "AA010": "# archagent-audit: ignore AA010\nsave_result(response.output_text)\n",
    "AA011": '# archagent-audit: ignore AA011\nagent = Agent(name="one")\n',
}


@pytest.mark.parametrize(("rule_id", "source"), JUDGMENT_SUPPRESSIONS.items())
def test_every_judgment_rule_suppression_prevents_code_sharing(
    tmp_path: Path,
    rule_id: str,
    source: str,
) -> None:
    (tmp_path / "agent.py").write_text(source, encoding="utf-8")
    client = FakeClient(SimpleNamespace(output_parsed=JudgmentBatch(findings=[]), output=[]))

    report = scan_path(
        tmp_path,
        judgment=True,
        send_code=True,
        judgment_client=client,
    )

    assert rule_id not in sent_rule_ids(client)
    assert report.suppressions >= 1


def test_judgment_can_return_a_clean_tool_schema_verdict(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        "@function_tool\ndef fetch_customer_by_id(customer_id: str):\n    return customer_id\n",
        encoding="utf-8",
    )
    client = FakeClient(
        SimpleNamespace(output_parsed=JudgmentBatch(findings=[]), output=[])
    )

    report = scan_path(
        tmp_path,
        judgment=True,
        send_code=True,
        judgment_client=client,
    )

    assert "AA009" in sent_rule_ids(client)
    assert "AA009" not in {item.rule_id for item in report.findings}
    assert report.judgment_status == "completed"
