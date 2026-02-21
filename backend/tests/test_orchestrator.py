import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from agent.llm import build_llm_messages
from db.models import EntryKind, EntryStatus


def _entry(kind, data, status=None, uploaded_file_id=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        kind=kind,
        data=data,
        status=status,
        uploaded_file_id=uploaded_file_id,
        created_at=datetime.now(timezone.utc),
    )


def test_user_message_text_only():
    entries = [_entry(EntryKind.USER_MESSAGE, {"content": "Can I park here?"})]
    messages = build_llm_messages(entries, "test system prompt")
    assert messages[0]["role"] == "system"
    user_msg = messages[1]
    assert user_msg["role"] == "user"
    assert user_msg["content"] == "Can I park here?"


def test_user_message_with_image():
    file_id = uuid.uuid4()
    entries = [
        _entry(
            EntryKind.USER_MESSAGE,
            {"content": "What does this say?"},
            uploaded_file_id=file_id,
        )
    ]
    messages = build_llm_messages(entries, "test system prompt")
    content = messages[1]["content"]
    assert "What does this say?" in content
    assert f"[User attached an image (file_id: {file_id})]" in content


def test_tool_call_and_result():
    entries = [
        _entry(
            EntryKind.TOOL_CALL,
            {"call_id": "c1", "tool_name": "get_current_time", "arguments": {}},
            status=EntryStatus.DONE,
        ),
        _entry(
            EntryKind.TOOL_RESULT,
            {"call_id": "c1", "result": {"datetime": "2025-01-01T00:00:00"}},
        ),
    ]
    messages = build_llm_messages(entries, "test system prompt")
    # system + tool_call + tool_result = 3
    assert len(messages) == 3
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] is None
    assert messages[1]["tool_calls"][0]["id"] == "c1"
    assert messages[2]["role"] == "tool"
    assert messages[2]["tool_call_id"] == "c1"


def test_skips_reasoning_and_sub_agent():
    entries = [
        _entry(EntryKind.REASONING, {"text": "thinking..."}),
        _entry(EntryKind.SUB_AGENT_CALL, {"child_session_id": "x"}),
        _entry(EntryKind.SUB_AGENT_RESULT, {"result": {}}),
        _entry(EntryKind.USER_MESSAGE, {"content": "hi"}),
    ]
    messages = build_llm_messages(entries, "test system prompt")
    # system + user_message only
    assert len(messages) == 2
    assert messages[1]["role"] == "user"
