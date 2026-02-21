import { useState } from "react";
import {
  Entry,
  EntryKind,
  ToolCallData,
  ToolResultData,
  ReasoningData,
  SubAgentCallData,
  SubAgentResultData,
} from "../types";

interface Props {
  entry: Entry;
}

const EVENT_META: Record<
  string,
  { icon: string; label: string }
> = {
  tool_call: { icon: "\uD83D\uDD27", label: "Tool Call" },
  tool_result: { icon: "\u2705", label: "Tool Result" },
  reasoning: { icon: "\uD83E\uDDE0", label: "Reasoning" },
  sub_agent_call: { icon: "\uD83E\uDD16", label: "Sub-Agent Call" },
  sub_agent_result: { icon: "\uD83E\uDD16", label: "Sub-Agent Result" },
};

function formatEventBody(kind: EntryKind, data: Entry["data"]): string {
  switch (kind) {
    case "tool_call": {
      const d = data as ToolCallData;
      return `${d.tool_name}(${JSON.stringify(d.arguments)})`;
    }
    case "tool_result": {
      const d = data as ToolResultData;
      return typeof d.result === "string"
        ? d.result
        : JSON.stringify(d.result, null, 2);
    }
    case "reasoning": {
      return (data as ReasoningData).content;
    }
    case "sub_agent_call": {
      const d = data as SubAgentCallData;
      return `Delegating to ${d.agent_name}`;
    }
    case "sub_agent_result": {
      const d = data as SubAgentResultData;
      return typeof d.result === "string"
        ? d.result
        : JSON.stringify(d.result, null, 2);
    }
    default:
      return JSON.stringify(data);
  }
}

export function EventCard({ entry }: Props) {
  const [expanded, setExpanded] = useState(false);
  const meta = EVENT_META[entry.kind] ?? { icon: "?", label: entry.kind };
  const body = formatEventBody(entry.kind, entry.data);

  return (
    <div className="event-card" onClick={() => setExpanded(!expanded)}>
      <div className="event-card-header">
        <span className="event-icon">{meta.icon}</span>
        <span className="event-label">{meta.label}</span>
        <span className="event-expand">{expanded ? "\u25B2" : "\u25BC"}</span>
      </div>
      {expanded && <pre className="event-card-body">{body}</pre>}
    </div>
  );
}
