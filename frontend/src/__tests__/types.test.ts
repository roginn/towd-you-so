import { describe, it, expect } from "vitest";
import { isMessageEntry, EntryKind } from "../types";

describe("isMessageEntry", () => {
  it("returns true for user_message", () => {
    expect(isMessageEntry("user_message")).toBe(true);
  });

  it("returns true for assistant_message", () => {
    expect(isMessageEntry("assistant_message")).toBe(true);
  });

  const debugKinds: EntryKind[] = [
    "tool_call",
    "tool_result",
    "reasoning",
    "sub_agent_call",
    "sub_agent_result",
  ];

  for (const kind of debugKinds) {
    it(`returns false for ${kind}`, () => {
      expect(isMessageEntry(kind)).toBe(false);
    });
  }
});
