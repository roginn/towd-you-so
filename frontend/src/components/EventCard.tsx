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
  resultEntry?: Entry;
}

const EVENT_META: Record<
  string,
  { icon: string; label: string }
> = {
  tool_call: { icon: "\uD83D\uDD27", label: "Tool Call" },
  reasoning: { icon: "\uD83E\uDDE0", label: "Reasoning" },
  sub_agent_call: { icon: "\uD83E\uDD16", label: "Sub-Agent Call" },
};

const STATUS_INDICATOR: Record<string, string> = {
  pending: "\u23F3",   // hourglass
  running: "\u25B6\uFE0F",   // play
  done: "\u2705",      // checkmark
  failed: "\u274C",    // X
};

function formatCallBody(kind: EntryKind, data: Entry["data"]): string {
  switch (kind) {
    case "tool_call": {
      const d = data as ToolCallData;
      return `${d.tool_name}(${JSON.stringify(d.arguments)})`;
    }
    case "reasoning": {
      return (data as ReasoningData).content;
    }
    case "sub_agent_call": {
      const d = data as SubAgentCallData;
      return `Delegating to ${d.agent_name}`;
    }
    default:
      return JSON.stringify(data);
  }
}

function formatResultBody(kind: EntryKind, data: Entry["data"]): string {
  switch (kind) {
    case "tool_result": {
      const d = data as ToolResultData;
      return typeof d.result === "string"
        ? d.result
        : JSON.stringify(d.result, null, 2);
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

export function EventCard({ entry, resultEntry }: Props) {
  const [expanded, setExpanded] = useState(false);
  const meta = EVENT_META[entry.kind] ?? { icon: "?", label: entry.kind };
  const body = formatCallBody(entry.kind, entry.data);
  const statusIcon = entry.status ? STATUS_INDICATOR[entry.status] : undefined;

  return (
    <div className="event-card" onClick={() => setExpanded(!expanded)}>
      <div className="event-card-header">
        <span className="event-icon">{meta.icon}</span>
        <span className="event-label">{meta.label}</span>
        {statusIcon && (
          <span className={`event-status event-status-${entry.status}`}>{statusIcon}</span>
        )}
        <span className="event-expand">{expanded ? "\u25B2" : "\u25BC"}</span>
      </div>
      {expanded && (
        <>
          <pre className="event-card-body">{body}</pre>
          {resultEntry && (
            <>
              <div className="event-result-divider">Result</div>
              <pre className="event-card-body">{formatResultBody(resultEntry.kind, resultEntry.data)}</pre>
            </>
          )}
        </>
      )}
    </div>
  );
}
