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
"""

    candidates = collect_judgment_candidates([("agent.py", source)])

    assert {item.rule_id for item in candidates} == {"AA003", "AA005", "AA008", "AA009", "AA011"}


def test_eval_marker_removes_aa011_candidate() -> None:
    sources = [
        ("agent.py", 'agent = Agent(name="one")\n'),
        ("test_agent.py", "# archagent-audit: eval agent\n"),
    ]

    candidates = collect_judgment_candidates(sources)

    assert "AA011" not in {item.rule_id for item in candidates}

