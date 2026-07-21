"""Dispatch Python source through all framework-specific evidence adapters."""

from __future__ import annotations

import ast

from uptocode.adapters.anthropic import extract_anthropic_evidence
from uptocode.adapters.crewai import extract_crewai_evidence
from uptocode.adapters.llamaindex import extract_llamaindex_evidence
from uptocode.adapters.pydantic_ai import extract_pydantic_ai_evidence
from uptocode.evidence import NormalizedEvidence


def extract_framework_evidence(tree: ast.Module, source: str, *, file: str) -> NormalizedEvidence:
    combined = NormalizedEvidence(language="python")
    for extractor in (
        extract_anthropic_evidence,
        extract_crewai_evidence,
        extract_pydantic_ai_evidence,
        extract_llamaindex_evidence,
    ):
        combined.merge(extractor(tree, source, file=file))
    return combined
