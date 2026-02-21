import json
import logging
import uuid

from agent.llm import LLMResponse, call_llm
from conductor.tool_executor import execute_tool
from db.models import EntryModel
from tools import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a parking sign reading specialist. "
    "Given an image URL, use the vision tool to describe the sign, "
    "then extract and return all parking rules, restrictions, and time windows. "
    "Return a concise plain-text summary of the sign's rules."
)

SUB_AGENT_TOOLS = ["vision", "get_current_time"]


def _get_tools(names: list[str]) -> list[dict]:
    return [d for d in TOOL_DEFINITIONS if d["function"]["name"] in names]


async def run_agent(
    entries: list[EntryModel] | None = None,
    uploaded_file_id: uuid.UUID | None = None,
) -> dict:
    """Run an internal LLM loop to analyze a parking sign image."""
    image_url = ""

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Read the parking sign in this image."},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        },
    ]

    tools = _get_tools(SUB_AGENT_TOOLS)

    for _ in range(10):  # guard against infinite loops
        llm_response: LLMResponse = await call_llm(messages, tools=tools)

        if llm_response.content:
            return {"text": llm_response.content}

        if not llm_response.tool_calls:
            return {"text": "Unable to read the parking sign."}

        for tc in llm_response.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tc.call_id,
                            "type": "function",
                            "function": {
                                "name": tc.tool_name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                    ],
                }
            )

            result = await execute_tool(tc.tool_name, tc.arguments)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.call_id,
                    "content": json.dumps(result),
                }
            )

    return {"text": "Unable to read the parking sign."}
