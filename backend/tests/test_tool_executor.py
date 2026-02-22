import uuid

import pytest

from worker.tool_executor import execute_tool


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
async def test_read_parking_sign_passes_file_id():
    from unittest.mock import AsyncMock, patch

    file_id = uuid.uuid4()
    mock_result = {"text": "No parking 9am-6pm"}
    with patch(
        "agent.subagents.parking_sign_reader.run_agent",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_run:
        result = await execute_tool("task_read_parking_sign", {"file_id": str(file_id)})
    assert result == mock_result
    mock_run.assert_called_once_with(uploaded_file_id=file_id)
