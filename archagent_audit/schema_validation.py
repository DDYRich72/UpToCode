"""Strict validation for MCP/function-tool descriptors."""

from __future__ import annotations

import re

from jsonschema import Draft202012Validator, SchemaError
from pydantic import Field

from archagent_audit.models import StrictModel


_TOOL_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


class SchemaIssue(StrictModel):
    field: str
    message: str


class ToolSchemaDescriptor(StrictModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=8, max_length=2_000)
    inputSchema: dict[str, object]


class ToolSchemaResult(StrictModel):
    valid: bool
    issues: list[SchemaIssue]
    judgment_status: str = "not-requested"


def validate_tool_schema(value: object) -> ToolSchemaResult:
    issues: list[SchemaIssue] = []
    if not isinstance(value, dict):
        return ToolSchemaResult(valid=False, issues=[SchemaIssue(field="$", message="Schema must be a JSON object.")])
    try:
        descriptor = ToolSchemaDescriptor.model_validate(value)
    except Exception as error:
        return ToolSchemaResult(valid=False, issues=[SchemaIssue(field="$", message=str(error))])
    if not _TOOL_NAME.fullmatch(descriptor.name):
        issues.append(SchemaIssue(field="name", message="Tool name contains unsupported characters."))
    schema = descriptor.inputSchema
    if schema.get("type") != "object":
        issues.append(SchemaIssue(field="inputSchema.type", message="Tool input schema must be an object."))
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        issues.append(SchemaIssue(field="inputSchema", message=error.message))
    properties = schema.get("properties", {})
    if properties is not None and not isinstance(properties, dict):
        issues.append(SchemaIssue(field="inputSchema.properties", message="properties must be an object."))
    elif isinstance(properties, dict):
        for name, definition in properties.items():
            if not isinstance(definition, dict) or not definition.get("description"):
                issues.append(SchemaIssue(field=f"inputSchema.properties.{name}", message="Property requires a description."))
    if schema.get("additionalProperties") is not False:
        issues.append(SchemaIssue(field="inputSchema.additionalProperties", message="Strict tools must set additionalProperties to false."))
    return ToolSchemaResult(valid=not issues, issues=issues)
