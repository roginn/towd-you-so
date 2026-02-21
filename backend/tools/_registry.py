import types

TOOL_DEFINITIONS: list[dict] = []
TOOL_REGISTRY: dict[str, types.ModuleType] = {}


def register(definition: dict, module: types.ModuleType) -> None:
    """Register a tool's OpenAI schema and backing module."""
    tool_name = definition["function"]["name"]
    TOOL_DEFINITIONS.append(definition)
    TOOL_REGISTRY[tool_name] = module
