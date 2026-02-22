import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from openai import AsyncOpenAI

from config import settings
from db.models import EntryKind

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


@dataclass
class ToolCallResult:
    call_id: str
    tool_name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCallResult] | None = None


# --- Streaming delta types ---


@dataclass
class ReasoningDelta:
    text: str


@dataclass
class ContentDelta:
    text: str


@dataclass
class ToolCallDelta:
    index: int
    call_id: str | None = None
    tool_name: str | None = None
    arguments_chunk: str = ""


@dataclass
class StreamDone:
    finish_reason: str


type StreamEvent = ReasoningDelta | ContentDelta | ToolCallDelta | StreamDone


def _tools_to_responses_format(tools: list[dict]) -> list[dict]:
    """Convert Chat Completions tool format to Responses API format."""
    result = []
    for t in tools:
        fn = t["function"]
        result.append({
            "type": "function",
            "name": fn["name"],
            "description": fn.get("description", ""),
            "parameters": fn.get("parameters", {}),
        })
    return result


async def call_llm_streaming(
    messages: list[dict], tools: list[dict] | None = None
) -> AsyncIterator[StreamEvent]:
    """Async generator yielding streaming events via the Responses API."""
    kwargs: dict = {
        "model": settings.OPENAI_MODEL,
        "input": messages,
        "reasoning": {"effort": "medium", "summary": "detailed"},
        "stream": True,
    }
    if tools:
        kwargs["tools"] = _tools_to_responses_format(tools)

    stream = await openai_client.responses.create(**kwargs)

    # Track tool calls by output_index so we can emit ToolCallDelta with call_id/name
    pending_tool_calls: dict[int, dict] = {}

    async for event in stream:
        etype = event.type

        # Reasoning summary deltas
        if etype == "response.reasoning_summary_text.delta":
            yield ReasoningDelta(text=event.delta)

        # Content text deltas
        elif etype == "response.output_text.delta":
            yield ContentDelta(text=event.delta)

        # Tool call: item added with name and call_id
        elif etype == "response.output_item.added":
            item = event.item
            if getattr(item, "type", None) == "function_call":
                idx = event.output_index
                pending_tool_calls[idx] = {
                    "call_id": item.call_id,
                    "tool_name": item.name,
                }
                yield ToolCallDelta(
                    index=idx,
                    call_id=item.call_id,
                    tool_name=item.name,
                )

        # Tool call arguments delta
        elif etype == "response.function_call_arguments.delta":
            idx = event.output_index
            yield ToolCallDelta(index=idx, arguments_chunk=event.delta)

        # Stream complete
        elif etype == "response.completed":
            yield StreamDone(finish_reason="stop")


async def call_llm(messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
    """Non-streaming LLM call using the Responses API."""
    kwargs: dict = {
        "model": settings.OPENAI_MODEL,
        "input": messages,
        "reasoning": {"effort": "medium"},
    }
    if tools:
        kwargs["tools"] = _tools_to_responses_format(tools)

    response = await openai_client.responses.create(**kwargs)

    # Collect tool calls and text content from output items
    tool_calls: list[ToolCallResult] = []
    content_parts: list[str] = []

    for item in response.output:
        if item.type == "function_call":
            tool_calls.append(
                ToolCallResult(
                    call_id=item.call_id,
                    tool_name=item.name,
                    arguments=json.loads(item.arguments),
                )
            )
        elif item.type == "message":
            for part in item.content:
                if hasattr(part, "text"):
                    content_parts.append(part.text)

    if tool_calls:
        return LLMResponse(tool_calls=tool_calls)

    return LLMResponse(content="".join(content_parts) or "")


def build_llm_messages(entries: list, system_prompt: str) -> list[dict]:
    """Map Entry rows to OpenAI chat message format per PRD §2.3.6."""
    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    for entry in entries:
        kind = entry.kind
        data = entry.data

        if kind == EntryKind.USER_MESSAGE:
            text = data.get("content", "")
            if entry.uploaded_file_id:
                text += f"\n[User attached an image (file_id: {entry.uploaded_file_id})]"
            messages.append({"role": "user", "content": text})

        elif kind == EntryKind.ASSISTANT_MESSAGE:
            messages.append({"role": "assistant", "content": data["content"]})

        elif kind == EntryKind.TOOL_CALL:
            tc_obj = {
                "id": data["call_id"],
                "type": "function",
                "function": {
                    "name": data["tool_name"],
                    "arguments": json.dumps(data["arguments"]),
                },
            }
            # Group consecutive tool_calls into a single assistant message
            if messages and messages[-1].get("tool_calls"):
                messages[-1]["tool_calls"].append(tc_obj)
            else:
                messages.append(
                    {"role": "assistant", "content": "", "tool_calls": [tc_obj]}
                )

        elif kind == EntryKind.TOOL_RESULT:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": data["call_id"],
                    "content": json.dumps(data["result"]),
                }
            )

        # reasoning, sub_agent_call, sub_agent_result are excluded

    return messages


def build_responses_input(entries: list, system_prompt: str) -> list[dict]:
    """Map Entry rows to OpenAI Responses API input format.

    Unlike Chat Completions, the Responses API represents tool calls and
    results as top-level items rather than nested in assistant messages.
    """
    items: list[dict] = [{"role": "system", "content": system_prompt}]

    for entry in entries:
        kind = entry.kind
        data = entry.data

        if kind == EntryKind.USER_MESSAGE:
            text = data.get("content", "")
            if entry.uploaded_file_id:
                text += f"\n[User attached an image (file_id: {entry.uploaded_file_id})]"
            items.append({"role": "user", "content": text})

        elif kind == EntryKind.ASSISTANT_MESSAGE:
            items.append({"role": "assistant", "content": data["content"]})

        elif kind == EntryKind.TOOL_CALL:
            items.append({
                "type": "function_call",
                "name": data["tool_name"],
                "arguments": json.dumps(data["arguments"]),
                "call_id": data["call_id"],
            })

        elif kind == EntryKind.TOOL_RESULT:
            items.append({
                "type": "function_call_output",
                "call_id": data["call_id"],
                "output": json.dumps(data["result"]),
            })

        # reasoning, sub_agent_call, sub_agent_result are excluded

    return items
