import json
import logging
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


async def call_llm(messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
    kwargs = {"model": settings.OPENAI_MODEL, "messages": messages}
    if tools:
        kwargs["tools"] = tools
    response = await openai_client.chat.completions.create(**kwargs)
    choice = response.choices[0]

    if choice.finish_reason == "tool_calls" or choice.message.tool_calls:
        return LLMResponse(
            tool_calls=[
                ToolCallResult(
                    call_id=tc.id,
                    tool_name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                )
                for tc in choice.message.tool_calls
            ]
        )

    return LLMResponse(content=choice.message.content or "")


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
                    {"role": "assistant", "content": None, "tool_calls": [tc_obj]}
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
