from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

# uptocode: eval agent
mcp = FastMCP("unsafe-records")


class Database:
    def delete(self, record_id: str) -> None:
        pass


database = Database()


class DeleteArgs(BaseModel):
    record_id: str


@mcp.tool()
def delete_record(args: DeleteArgs) -> str:
    try:
        database.delete(args.record_id)
    except Exception:
        return "Operation failed"
    return "Deleted"


instructions = "Always get approval before deleting records."
mcp.run(transport="streamable-http")
