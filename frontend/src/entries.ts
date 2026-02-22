import { Entry, ToolCallData, SubAgentCallData, isMessageEntry } from "./types";

/** Build a lookup from call_id/child_session_id → result entry */
export function buildResultByCallId(entries: Entry[]): Map<string, Entry> {
  const map = new Map<string, Entry>();
  for (const e of entries) {
    if (e.kind === "tool_result") {
      const d = e.data as { call_id: string };
      map.set(d.call_id, e);
    } else if (e.kind === "sub_agent_result") {
      const d = e.data as { child_session_id: string };
      map.set(d.child_session_id, e);
    }
  }
  return map;
}

/** Filter entries to only those visible given the current mode */
export function visibleEntries(entries: Entry[], debugMode: boolean): Entry[] {
  return debugMode
    ? entries.filter((e) => e.kind !== "tool_result" && e.kind !== "sub_agent_result")
    : entries.filter((e) => isMessageEntry(e.kind));
}

/** Find the result entry that matches a call entry */
export function getResultEntry(
  entry: Entry,
  resultByCallId: Map<string, Entry>,
): Entry | undefined {
  if (entry.kind === "tool_call") {
    return resultByCallId.get((entry.data as ToolCallData).call_id);
  }
  if (entry.kind === "sub_agent_call") {
    return resultByCallId.get((entry.data as SubAgentCallData).child_session_id);
  }
  return undefined;
}
