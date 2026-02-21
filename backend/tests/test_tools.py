import pytest

from tools import read_parking_sign, time_utils, vision


@pytest.mark.asyncio
async def test_read_parking_sign():
    result = await read_parking_sign.run(image_url="http://example.com/sign.jpg")
    assert "text" in result
    assert isinstance(result["text"], str)


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
