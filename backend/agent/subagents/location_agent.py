import json
import logging
import uuid

from agent.llm import call_llm
from db.database import get_db
from db.models import EntryKind
from db.repository import append_entry
from interface.models import entry_to_wire
from tools import TOOL_DEFINITIONS, TOOL_REGISTRY
from worker.registry import push_to_client

logger = logging.getLogger(__name__)

LOCATION_AGENT_TOOLS = [
    "mapbox_geocode",
    "geo_midpoint",
    "geo_distance",
    "save_parking_sign_location",
    "search_nearby_signs",
]

SYSTEM_PROMPT = (
    "You are a location specialist for a parking sign assistant app.\n\n"
    "You can geocode locations, calculate distances and midpoints, save parking sign locations, "
    "and search for nearby saved signs.\n\n"
    "Guidelines:\n"
    "- When given a natural-language location like '20th st between illinois and georgia st, SF', "
    "geocode both cross-street intersections (e.g. '20th st & illinois st, San Francisco' and "
    "'20th st & georgia st, San Francisco') and compute the midpoint to get the sign's location.\n"
    "- When geocoding, always include the city/state if provided by the user for better accuracy.\n"
    "- When saving a sign location, use the midpoint coordinates, the user's original description, "
    "and the provided sign_text and uploaded_file_id.\n"
    "- When searching for nearby signs, geocode the user's described location first, then search.\n"
    "- Default search radius is 1600 meters (~1 mile).\n"
    "- Return clear, structured results. When returning search results, include distance and sign rules.\n"
    "- When done, respond with a summary of what you did and the key results."
)


def _get_tools() -> list[dict]:
    return [d for d in TOOL_DEFINITIONS if d["function"]["name"] in LOCATION_AGENT_TOOLS]


async def run_agent(
    task_description: str,
    session_id: uuid.UUID | None = None,
    uploaded_file_id: str | None = None,
    sign_text: str | None = None,
) -> dict:
    """Run the location sub-agent with an LLM reasoning loop."""
    user_content = f"Task: {task_description}"
    if uploaded_file_id:
        user_content += f"\n\nuploaded_file_id: {uploaded_file_id}"
    if sign_text:
        user_content += f"\n\nsign_text: {sign_text}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    tools = _get_tools()
    actions_taken = []

    for _turn in range(5):
        response = await call_llm(messages, tools=tools)

        if response.tool_calls:
            for tc in response.tool_calls:
                messages.append({
                    "type": "function_call",
                    "name": tc.tool_name,
                    "arguments": json.dumps(tc.arguments),
                    "call_id": tc.call_id,
                })

                if session_id:
                    tool_call_data = {
                        "call_id": tc.call_id,
                        "tool_name": tc.tool_name,
                        "arguments": tc.arguments,
                        "agent_name": "location_agent",
                    }
                    async with get_db() as db:
                        tc_entry = await append_entry(
                            db, session_id, EntryKind.TOOL_CALL, tool_call_data
                        )
                    await push_to_client(session_id, entry_to_wire(tc_entry))

                module = TOOL_REGISTRY.get(tc.tool_name)
                if module:
                    result = await module.run(**tc.arguments)
                    actions_taken.append(f"{tc.tool_name}: {json.dumps(result)}")
                else:
                    result = {"error": f"Unknown tool: {tc.tool_name}"}

                if session_id:
                    tool_result_data = {
                        "call_id": tc.call_id,
                        "result": result,
                    }
                    async with get_db() as db:
                        tr_entry = await append_entry(
                            db, session_id, EntryKind.TOOL_RESULT, tool_result_data
                        )
                    await push_to_client(session_id, entry_to_wire(tr_entry))

                messages.append({
                    "type": "function_call_output",
                    "call_id": tc.call_id,
                    "output": json.dumps(result),
                })
        else:
            summary = response.content or "Location task completed."
            return {"summary": summary, "actions": actions_taken}

    return {"summary": "Location agent completed (max turns reached).", "actions": actions_taken}
