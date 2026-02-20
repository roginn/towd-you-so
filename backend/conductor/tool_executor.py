from tools import read_parking_sign, time_utils, vision

_TOOL_REGISTRY: dict[str, object] = {
    "read_parking_sign": read_parking_sign,
    "vision": vision,
    "get_current_time": time_utils,
}


async def execute_tool(tool_name: str, arguments: dict) -> dict:
    """Dispatch a tool call to the matching tool module's run() function."""
    module = _TOOL_REGISTRY.get(tool_name)
    if module is None:
        return {"error": f"Unknown tool: {tool_name}"}
    return await module.run(**arguments)
