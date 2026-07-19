"""Minimal trusted local ArchAgent rulepack example."""

from archagent_audit.models import AnalysisWarning
from archagent_audit.rules.plugins import RuleContext, RulePluginResult


class ExampleRulepack:
    api_version = "1.0"

    def evaluate(self, context: RuleContext) -> RulePluginResult:
        if not context.files:
            return RulePluginResult(
                warnings=[
                    AnalysisWarning(
                        code="EXAMPLE/EMPTY_PROJECT",
                        message="The example pack received no normalized Python files.",
                    )
                ]
            )
        return RulePluginResult()


plugin = ExampleRulepack()
