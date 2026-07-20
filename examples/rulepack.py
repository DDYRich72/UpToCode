"""Minimal trusted local UpToCode rulepack example."""

from uptocode.models import AnalysisWarning
from uptocode.rules.plugins import RuleContext, RulePluginResult


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
