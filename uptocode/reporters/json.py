"""JSON rendering."""

from uptocode.models import Report


def render_json(report: Report) -> str:
    return report.model_dump_json(indent=2)

