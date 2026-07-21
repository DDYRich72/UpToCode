import logging

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, ValidationError

# uptocode: eval agent
logger = logging.getLogger(__name__)
token_verifier = object()
mcp = FastMCP("safe-records", auth=token_verifier)
READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)


class LookupArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_id: str


@mcp.tool(annotations=READ_ONLY)
def lookup_record(args: LookupArgs) -> dict[str, object]:
    try:
        logger.info("looking up record")
        return {"record_id": args.record_id}
    except ValidationError:
        return {"isError": True, "category": "validation", "retryable": False}


mcp.run(transport="streamable-http")
