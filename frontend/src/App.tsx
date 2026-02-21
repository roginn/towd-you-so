import { useState, useRef, useEffect, FormEvent } from "react";
import { Entry, isMessageEntry } from "./types";
import { MessageBubble } from "./components/MessageBubble";
import { EventCard } from "./components/EventCard";
import { MOCK_ENTRIES } from "./mockData";

function App() {
  const [entries, setEntries] = useState<Entry[]>(MOCK_ENTRIES);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, debugMode]);

  const visibleEntries = debugMode
    ? entries
    : entries.filter((e) => isMessageEntry(e.kind));

  const sendMessage = async (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const userEntry: Entry = {
      id: crypto.randomUUID(),
      sessionId: "",
      kind: "user_message",
      data: { content: text },
      createdAt: new Date().toISOString(),
    };
    const updated = [...entries, userEntry];
    setEntries(updated);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: updated
            .filter((e) => isMessageEntry(e.kind))
            .map((e) => ({
              role: e.kind === "user_message" ? "user" : "assistant",
              content: (e.data as { content: string }).content,
            })),
        }),
      });

      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }

      const data = await res.json();
      setEntries([
        ...updated,
        {
          id: crypto.randomUUID(),
          sessionId: "",
          kind: "assistant_message",
          data: { content: data.reply },
          createdAt: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Unknown error";
      setEntries([
        ...updated,
        {
          id: crypto.randomUUID(),
          sessionId: "",
          kind: "assistant_message",
          data: { content: `Error: ${errorMessage}` },
          createdAt: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>Tow'd You So</h1>
        <label className="debug-toggle">
          <input
            type="checkbox"
            checked={debugMode}
            onChange={(e) => setDebugMode(e.target.checked)}
          />
          Debug
        </label>
      </header>
      <div className="messages">
        {entries.length === 0 && (
          <div className="empty-state">Send a message to start chatting</div>
        )}
        {visibleEntries.map((entry) =>
          isMessageEntry(entry.kind) ? (
            <MessageBubble key={entry.id} entry={entry} />
          ) : (
            <EventCard key={entry.id} entry={entry} />
          )
        )}
        {loading && (
          <div className="message assistant">
            <div className="bubble loading-bubble">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form className="input-bar" onSubmit={sendMessage}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}

export default App;
