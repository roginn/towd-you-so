export type EntryKind =
  | "user_message"
  | "assistant_message"
  | "tool_call"
  | "tool_result"
  | "reasoning"
  | "sub_agent_call"
  | "sub_agent_result";

export interface Entry {
  id: string;
  sessionId: string;
  kind: EntryKind;
  data: EntryData;
  createdAt: string;
}

// Discriminated data shapes per kind
export type EntryData =
  | UserMessageData
  | AssistantMessageData
  | ToolCallData
  | ToolResultData
  | ReasoningData
  | SubAgentCallData
  | SubAgentResultData;

export interface UserMessageData {
  content: string;
  image_url?: string;
}

export interface AssistantMessageData {
  content: string;
}

export interface ToolCallData {
  call_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
}

export interface ToolResultData {
  call_id: string;
  result: unknown;
}

export interface ReasoningData {
  content: string;
}

export interface SubAgentCallData {
  child_session_id: string;
  agent_name: string;
}

export interface SubAgentResultData {
  child_session_id: string;
  result: unknown;
}

/** Whether an entry kind is a chat message (always visible) or a debug event (toggleable) */
export function isMessageEntry(kind: EntryKind): boolean {
  return kind === "user_message" || kind === "assistant_message";
}
