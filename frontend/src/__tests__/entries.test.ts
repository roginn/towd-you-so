import { describe, it, expect } from "vitest";
import { Entry } from "../types";
import { buildResultByCallId, visibleEntries, getResultEntry } from "../entries";

/** Helper to build a minimal Entry */
function entry(kind: Entry["kind"], data: Entry["data"], id = "e-" + Math.random()): Entry {
  return { id, sessionId: "s1", kind, data, createdAt: new Date().toISOString() };
}

const userMsg = entry("user_message", { content: "hello" });
const assistantMsg = entry("assistant_message", { content: "hi" });
const toolCall = entry("tool_call", { call_id: "tc1", tool_name: "bash", arguments: {} });
const toolResult = entry("tool_result", { call_id: "tc1", result: "ok" });
const reasoning = entry("reasoning", { content: "thinking..." });
const subCall = entry("sub_agent_call", { call_id: "cs1", agent_name: "helper" });
const subResult = entry("sub_agent_result", { call_id: "cs1", result: "done" });

const allEntries = [userMsg, assistantMsg, toolCall, toolResult, reasoning, subCall, subResult];

describe("visibleEntries", () => {
  it("in normal mode, returns only user and assistant messages", () => {
    const result = visibleEntries(allEntries, false);
    expect(result).toEqual([userMsg, assistantMsg]);
  });

  it("in debug mode, excludes tool_result and sub_agent_result but keeps everything else", () => {
    const result = visibleEntries(allEntries, true);
    expect(result).toEqual([userMsg, assistantMsg, toolCall, reasoning, subCall]);
  });
});

describe("buildResultByCallId", () => {
  it("pairs tool_call with tool_result by call_id", () => {
    const map = buildResultByCallId(allEntries);
    expect(map.get("tc1")).toBe(toolResult);
  });

  it("pairs sub_agent_call with sub_agent_result by call_id", () => {
    const map = buildResultByCallId(allEntries);
    expect(map.get("cs1")).toBe(subResult);
  });
});

describe("getResultEntry", () => {
  const map = buildResultByCallId(allEntries);

  it("returns the matching tool_result for a tool_call", () => {
    expect(getResultEntry(toolCall, map)).toBe(toolResult);
  });

  it("returns the matching sub_agent_result for a sub_agent_call", () => {
    expect(getResultEntry(subCall, map)).toBe(subResult);
  });

  it("returns undefined for a message entry", () => {
    expect(getResultEntry(userMsg, map)).toBeUndefined();
  });
});
