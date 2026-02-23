import { describe, it, expect } from "vitest";
import { formatCallBody, formatResultBody } from "../components/EventCard";

describe("formatCallBody", () => {
  it("formats tool_call as toolName({...})", () => {
    const data = { call_id: "c1", tool_name: "readFile", arguments: { path: "/tmp" } };
    expect(formatCallBody("tool_call", data)).toBe('readFile({"path":"/tmp"})');
  });

  it("formats reasoning as content string", () => {
    const data = { content: "Let me think about this..." };
    expect(formatCallBody("reasoning", data)).toBe("Let me think about this...");
  });

  it("formats sub_agent_call as delegation message", () => {
    const data = { call_id: "s1", agent_name: "researcher" };
    expect(formatCallBody("sub_agent_call", data)).toBe("Delegating to researcher");
  });
});

describe("formatResultBody", () => {
  it("returns string result as-is for tool_result", () => {
    const data = { call_id: "c1", result: "file contents here" };
    expect(formatResultBody("tool_result", data)).toBe("file contents here");
  });

  it("returns pretty JSON for object result in tool_result", () => {
    const data = { call_id: "c1", result: { ok: true, count: 3 } };
    expect(formatResultBody("tool_result", data)).toBe(
      JSON.stringify({ ok: true, count: 3 }, null, 2),
    );
  });

  it("returns string result as-is for sub_agent_result", () => {
    const data = { call_id: "s1", result: "done" };
    expect(formatResultBody("sub_agent_result", data)).toBe("done");
  });

  it("returns pretty JSON for object result in sub_agent_result", () => {
    const data = { call_id: "s1", result: { status: "complete" } };
    expect(formatResultBody("sub_agent_result", data)).toBe(
      JSON.stringify({ status: "complete" }, null, 2),
    );
  });
});
