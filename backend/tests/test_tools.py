import uuid
from unittest.mock import AsyncMock, patch

import pytest

from db.models import EntryKind, EntryModel
from tools import read_parking_sign, time_utils, vision
from tools.context import ToolContext


@pytest.mark.asyncio
async def test_read_parking_sign():
    session_id = uuid.uuid4()
    file_id = uuid.uuid4()
    entry = EntryModel(
        session_id=session_id,
        kind=EntryKind.USER_MESSAGE,
        data={"content": "Can I park?"},
        uploaded_file_id=file_id,
    )
    context = ToolContext(session_id=session_id, entries=[entry], uploaded_file_id=file_id)

    mock_result = {"text": "No parking 9am-6pm Mon-Fri"}
    with patch(
        "agent.subagents.parking_sign_reader.run_agent",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_run:
        result = await read_parking_sign.run(context=context)
        mock_run.assert_called_once_with(entries=[entry], uploaded_file_id=file_id)
    assert result == mock_result


@pytest.mark.asyncio
async def test_read_parking_sign_no_context():
    result = await read_parking_sign.run()
    assert result == {"error": "No context provided to read_parking_sign"}


@pytest.mark.asyncio
async def test_time_utils():
    result = await time_utils.run()
    assert "datetime" in result
    assert "day_of_week" in result


@pytest.mark.asyncio
async def test_vision():
    result = await vision.run(image_url="http://example.com/img.jpg")
    assert "description" in result
    assert isinstance(result["description"], str)
