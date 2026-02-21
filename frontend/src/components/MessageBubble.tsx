import { Entry } from "../types";

interface Props {
  entry: Entry;
}

export function MessageBubble({ entry }: Props) {
  const role = entry.kind === "user_message" ? "user" : "assistant";
  const content = (entry.data as { content: string }).content;

  return (
    <div className={`message ${role}`}>
      <div className="bubble">{content}</div>
    </div>
  );
}
