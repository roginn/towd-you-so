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
  const [pendingFile, setPendingFile] = useState<{ file: File; preview: string } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, debugMode]);

  const visibleEntries = debugMode
    ? entries
    : entries.filter((e) => isMessageEntry(e.kind));

  const clearPendingFile = () => {
    if (pendingFile) {
      URL.revokeObjectURL(pendingFile.preview);
      setPendingFile(null);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      clearPendingFile();
      setPendingFile({ file, preview: URL.createObjectURL(file) });
    }
    e.target.value = "";
  };

  const sendMessage = async (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if ((!text && !pendingFile) || loading) return;

    let imageUrl: string | undefined;

    if (pendingFile) {
      try {
        const formData = new FormData();
        formData.append("file", pendingFile.file);
        const uploadRes = await fetch("http://localhost:8000/api/upload", {
          method: "POST",
          body: formData,
        });
        if (!uploadRes.ok) throw new Error(`Upload failed: ${uploadRes.status}`);
        const uploadData = await uploadRes.json();
        imageUrl = uploadData.url;
      } catch (err) {
        // Fall back to local preview if upload fails
        imageUrl = pendingFile.preview;
      }
      clearPendingFile();
    }

    const userEntry: Entry = {
      id: crypto.randomUUID(),
      sessionId: "",
      kind: "user_message",
      data: { content: text, ...(imageUrl ? { image_url: imageUrl } : {}) },
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
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        onChange={handleFileSelect}
      />
      {pendingFile && (
        <div className="image-preview">
          <div className="image-preview-thumb">
            <img src={pendingFile.preview} alt="Preview" />
            <button className="image-preview-remove" onClick={clearPendingFile} type="button">
              &times;
            </button>
          </div>
        </div>
      )}
      <form className="input-bar" onSubmit={sendMessage}>
        <button
          type="button"
          className="attach-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          aria-label="Attach image"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
          </svg>
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || (!input.trim() && !pendingFile)}>
          Send
        </button>
      </form>
    </div>
  );
}

export default App;
