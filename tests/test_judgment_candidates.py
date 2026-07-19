from archagent_audit.judgment_candidates import collect_judgment_candidates


def test_extracts_ambiguous_judgment_candidates_without_verdicts() -> None:
    source = """
from agents import Agent, function_tool
first = Agent(name="first")
second = Agent(name="second")
external = requests.get(url)
client.responses.create(model="gpt", input=external)

@function_tool
def process_record(value):
    database.write(value)

save_result(response.output_text)
"""

    candidates = collect_judgment_candidates([("agent.py", source)])

    assert {item.rule_id for item in candidates} == {"AA003", "AA005", "AA008", "AA009", "AA010", "AA011"}


def test_eval_marker_removes_aa011_candidate() -> None:
    sources = [
        ("agent.py", 'agent = Agent(name="one")\n'),
        ("test_agent.py", "# archagent-audit: eval agent\n"),
    ]

    candidates = collect_judgment_candidates(sources)

    assert "AA011" not in {item.rule_id for item in candidates}


def test_validated_output_is_not_an_aa010_judgment_candidate() -> None:
    candidates = collect_judgment_candidates(
        [
            (
                "agent.py",
                'save_result(SafeResult.model_validate({"text": response.output_text}))\n',
            )
        ]
    )

    assert "AA010" not in {item.rule_id for item in candidates}


def test_judgment_false_positive_regressions_do_not_create_candidates() -> None:
    cases = {
        "AA003": "@function_tool(needs_approval=True)\ndef delete_user(value):\n    database.delete(value)\n",
        "AA005": 'external = requests.get(url)\nsafe = sanitize(external)\nclient.responses.create(model="gpt", input=safe)\n',
        "AA008": 'agent = Agent(name="one")\n',
        "AA010": 'save_result(SafeResult.model_validate({"text": response.output_text}))\n',
        "AA011": 'agent = Agent(name="one")\n# archagent-audit: eval agent\n',
    }

    for rule_id, source in cases.items():
        candidates = collect_judgment_candidates([("agent.py", source)])
        assert rule_id not in {item.rule_id for item in candidates}
