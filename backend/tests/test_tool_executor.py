import uuid

import pytest

from conductor.tool_executor import execute_tool
from db.models import EntryKind, EntryModel
from tools.context import ToolContext


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
async def test_context_forwarded_to_read_parking_sign():
    from unittest.mock import AsyncMock, patch

    session_id = uuid.uuid4()
    file_id = uuid.uuid4()
    entry = EntryModel(
        session_id=session_id,
        kind=EntryKind.USER_MESSAGE,
        data={"content": "Can I park?"},
        uploaded_file_id=file_id,
    )
    context = ToolContext(session_id=session_id, entries=[entry], uploaded_file_id=file_id)

    mock_result = {"text": "No parking 9am-6pm"}
    with patch(
        "agent.subagents.parking_sign_reader.run_agent",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        result = await execute_tool("read_parking_sign", {}, context=context)
    assert result == mock_result
