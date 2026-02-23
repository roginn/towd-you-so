import types

TOOL_DEFINITIONS: list[dict] = []
TOOL_REGISTRY: dict[str, types.ModuleType] = {}
SUB_AGENT_TOOLS: dict[str, str] = {}  # tool_name -> agent display name


def register(definition: dict, module: types.ModuleType, *, agent_name: str | None = None) -> None:
    """Register a tool's OpenAI schema and backing module."""
    tool_name = definition["function"]["name"]
    TOOL_DEFINITIONS.append(definition)
    TOOL_REGISTRY[tool_name] = module
    if agent_name:
        SUB_AGENT_TOOLS[tool_name] = agent_name
