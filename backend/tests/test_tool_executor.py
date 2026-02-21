import pytest

from conductor.tool_executor import execute_tool


@pytest.mark.asyncio
async def test_known_tool_dispatches():
    result = await execute_tool("get_current_time", {})
    assert "datetime" in result
    assert "day_of_week" in result


@pytest.mark.asyncio
async def test_unknown_tool_returns_error():
    result = await execute_tool("nonexistent_tool", {})
    assert result == {"error": "Unknown tool: nonexistent_tool"}


@pytest.mark.asyncio
async def test_arguments_forwarded():
    result = await execute_tool("read_parking_sign", {"image_url": "http://example.com/img.jpg"})
    assert "text" in result
