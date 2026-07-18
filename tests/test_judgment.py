from __future__ import annotations

from types import SimpleNamespace

import pytest

from archagent_audit.engine import scan_path
from archagent_audit.judgment import (
    JudgmentBatch,
    JudgmentFinding,
    run_judgment,
)
from archagent_audit.judgment_candidates import JudgmentCandidate
from archagent_audit.models import Coverage, Report


SECRET = "sk-proj-abcdefghijklmnopqrstuvwxyz123456"


def candidate(rule_id: str = "AA009") -> JudgmentCandidate:
    return JudgmentCandidate(
        rule_id=rule_id,
        file="agent.py",
        line=4,
        evidence="Tool schema needs review.",
        excerpt=f'key = "{SECRET}"\n@function_tool\ndef act(value): ...',
    )


def parsed_finding(rule_id: str = "AA009") -> JudgmentFinding:
    return JudgmentFinding(
        rule_id=rule_id,
        file="agent.py",
        line=4,
        title="Poor tool schema",
        severity="warning",
        observed="The tool name and parameter contract are ambiguous.",
        implies="The model may select or call the tool incorrectly.",
        recommended="Use a specific name and constrained parameter schema.",
        tradeoff="A narrower schema is less flexible.",
        citation_url="https://developers.openai.com/api/docs/guides/function-calling",
    )


class FakeResponses:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, object]] = []

    def parse(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes: list[object]) -> None:
        self.responses = FakeResponses(outcomes)


def empty_report() -> Report:
    return Report(scan_root=".", coverage=Coverage(files_discovered=1, files_analyzed=1))


def success_response(rule_id: str = "AA009") -> object:
    return SimpleNamespace(
        output_parsed=JudgmentBatch(findings=[parsed_finding(rule_id)]),
        output=[],
    )


def test_structured_success_adds_judgment_finding_and_redacts_payload() -> None:
    client = FakeClient([success_response()])
    report = empty_report()

    run_judgment(report, [candidate()], client=client)

    assert report.judgment_status == "completed"
    assert [finding.rule_id for finding in report.findings] == ["AA009"]
    assert report.findings[0].tier == "judgment"
    payload = str(client.responses.calls[0])
    assert SECRET not in payload
    assert "[REDACTED:openai-api-key]" in payload
    assert client.responses.calls[0]["model"] == "gpt-5.6"
    assert client.responses.calls[0]["text_format"] is JudgmentBatch


def test_refusal_preserves_static_results_and_records_failure() -> None:
    client = FakeClient([SimpleNamespace(output_parsed=None, output=[{"type": "refusal"}])])
    report = empty_report()

    run_judgment(report, [candidate()], client=client)

    assert report.findings == []
    assert report.judgment_status == "failed"
    assert [warning.code for warning in report.analysis_warnings] == ["JUDGMENT_REFUSED"]


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (TimeoutError("slow"), "JUDGMENT_TIMEOUT"),
        (type("AuthenticationError", (Exception,), {})("bad key"), "JUDGMENT_AUTHENTICATION_FAILED"),
    ],
)
def test_failures_are_classified_without_raw_model_findings(
    error: Exception,
    code: str,
) -> None:
    client = FakeClient([error])
    report = empty_report()

    run_judgment(report, [candidate()], client=client)

    assert report.findings == []
    assert report.judgment_status == "failed"
    assert report.analysis_warnings[0].code == code


def test_one_rule_failure_and_one_success_is_partial() -> None:
    client = FakeClient([TimeoutError("slow"), success_response("AA011")])
    report = empty_report()
    candidates = [candidate("AA009"), candidate("AA011")]

    run_judgment(report, candidates, client=client)

    assert report.judgment_status == "partial"
    assert [finding.rule_id for finding in report.findings] == ["AA011"]
    assert len(client.responses.calls) == 2


def test_payload_is_bounded() -> None:
    long_candidate = JudgmentCandidate(
        rule_id="AA009",
        file="agent.py",
        line=1,
        evidence="review",
        excerpt="x" * 20_000,
    )
    client = FakeClient([success_response()])

    run_judgment(empty_report(), [long_candidate], client=client)

    assert len(str(client.responses.calls[0]["input"])) < 10_000


def test_scan_path_requires_explicit_code_sharing(tmp_path) -> None:
    (tmp_path / "agent.py").write_text(
        "# agent tool\n# reviewed candidate\n@function_tool\ndef vague(value):\n    return value\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="send-code"):
        scan_path(tmp_path, judgment=True)


def test_scan_path_collects_candidates_and_runs_injected_judgment(tmp_path) -> None:
    (tmp_path / "agent.py").write_text(
        "# agent tool\n# reviewed candidate\n@function_tool\ndef vague(value):\n    return value\n",
        encoding="utf-8",
    )
    client = FakeClient([success_response()])

    report = scan_path(
        tmp_path,
        judgment=True,
        send_code=True,
        judgment_client=client,
    )

    assert report.judgment_status == "completed"
    assert any(finding.rule_id == "AA009" and finding.tier == "judgment" for finding in report.findings)
    assert len(client.responses.calls) == 1
