import uuid
from unittest.mock import AsyncMock, patch

import pytest

from tools import read_parking_sign, time_utils


@pytest.mark.asyncio
async def test_read_parking_sign():
    file_id = uuid.uuid4()

    mock_result = {"text": "No parking 9am-6pm Mon-Fri"}
    with patch(
        "agent.subagents.parking_sign_reader.run_agent",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_run:
        result = await read_parking_sign.run(file_id=str(file_id))
        mock_run.assert_called_once_with(uploaded_file_id=file_id)
    assert result == mock_result


@pytest.mark.asyncio
async def test_time_utils():
    result = await time_utils.run()
    assert "datetime" in result
    assert "day_of_week" in result
