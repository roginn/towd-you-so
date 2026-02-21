from tools import TOOL_REGISTRY
from tools.context import ToolContext


async def execute_tool(
    tool_name: str, arguments: dict, context: ToolContext | None = None
) -> dict:
    """Dispatch a tool call to the matching tool module's run() function."""
    module = TOOL_REGISTRY.get(tool_name)
    if module is None:
        return {"error": f"Unknown tool: {tool_name}"}
    return await module.run(context=context, **arguments)
