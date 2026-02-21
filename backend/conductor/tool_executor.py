from tools import TOOL_REGISTRY


async def execute_tool(tool_name: str, arguments: dict) -> dict:
    """Dispatch a tool call to the matching tool module's run() function."""
    module = TOOL_REGISTRY.get(tool_name)
    if module is None:
        return {"error": f"Unknown tool: {tool_name}"}
    return await module.run(**arguments)
