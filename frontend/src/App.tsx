import { useState, useRef, useEffect, useCallback, FormEvent } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Entry, ToolCallData, SubAgentCallData, isMessageEntry } from "./types";
import { MessageBubble } from "./components/MessageBubble";
import { EventCard } from "./components/EventCard";
import { Paperclip } from "lucide-react";

const API_BASE = "/api";
const WS_BASE = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`;

function App() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [entries, setEntries] = useState<Entry[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const [pendingFile, setPendingFile] = useState<{ file: File; preview: string } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingMessageRef = useRef<{ content: string; file_id?: string } | null>(null);

  // Scroll to bottom when entries change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, debugMode]);

  // Load existing entries when navigating to a session
  useEffect(() => {
    if (!sessionId) return;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/sessions/${sessionId}/entries`);
        if (res.ok) {
          const data = await res.json();
          setEntries(
            data.map((e: any) => ({
              id: e.id,
              sessionId: e.session_id,
              kind: e.kind,
              data: e.data,
              createdAt: e.created_at,
              status: e.status,
            }))
          );
        }
      } catch {
        // Session may be new with no entries yet
      }
    })();
  }, [sessionId]);

  // WebSocket connection management
  const connectWebSocket = useCallback(
    (sid: string) => {
      if (wsRef.current) {
        wsRef.current.close();
      }

      const ws = new WebSocket(`${WS_BASE}/ws/${sid}`);
      wsRef.current = ws;

      ws.onopen = () => {
        // If we have a pending message (from session creation), send it now
        if (pendingMessageRef.current) {
          ws.send(JSON.stringify(pendingMessageRef.current));
          pendingMessageRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === "entry") {
          const e = msg.entry;
          const entry: Entry = {
            id: e.id,
            sessionId: e.session_id,
            kind: e.kind,
            data: e.data,
            createdAt: e.created_at,
            status: e.status,
          };
          setEntries((prev) => {
            // Replace if entry already exists (status update), otherwise append
            const idx = prev.findIndex((p) => p.id === entry.id);
            if (idx >= 0) {
              const updated = [...prev];
              updated[idx] = entry;
              return updated;
            }
            return [...prev, entry];
          });
        }

        if (msg.type === "status") {
          setEntries((prev) => {
            const idx = prev.findIndex((p) => p.id === msg.entry_id);
            if (idx >= 0) {
              const updated = [...prev];
              updated[idx] = { ...updated[idx], status: msg.status };
              return updated;
            }
            return prev;
          });
        }

        if (msg.type === "turn_complete") {
          setLoading(false);
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
      };

      ws.onerror = () => {
        setLoading(false);
      };
    },
    []
  );

  // Connect WebSocket when sessionId is available
  useEffect(() => {
    if (!sessionId) return;
    connectWebSocket(sessionId);
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [sessionId, connectWebSocket]);

  // Build lookup: call_id → tool_result/sub_agent_result entry
  const resultByCallId = new Map<string, Entry>();
  for (const e of entries) {
    if (e.kind === "tool_result") {
      const d = e.data as { call_id: string };
      resultByCallId.set(d.call_id, e);
    } else if (e.kind === "sub_agent_result") {
      const d = e.data as { child_session_id: string };
      resultByCallId.set(d.child_session_id, e);
    }
  }

  const visibleEntries = debugMode
    ? entries.filter((e) => e.kind !== "tool_result" && e.kind !== "sub_agent_result")
    : entries.filter((e) => isMessageEntry(e.kind));

  /** Find the result entry that matches a call entry */
  const getResultEntry = (entry: Entry): Entry | undefined => {
    if (entry.kind === "tool_call") {
      return resultByCallId.get((entry.data as ToolCallData).call_id);
    }
    if (entry.kind === "sub_agent_call") {
      return resultByCallId.get((entry.data as SubAgentCallData).child_session_id);
    }
    return undefined;
  };

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

    setInput("");
    setLoading(true);

    let fileId: string | undefined;

    // Upload file if attached
    if (pendingFile) {
      try {
        const formData = new FormData();
        formData.append("file", pendingFile.file);
        const uploadRes = await fetch(`${API_BASE}/upload`, {
          method: "POST",
          body: formData,
        });
        if (!uploadRes.ok) throw new Error(`Upload failed: ${uploadRes.status}`);
        const uploadData = await uploadRes.json();
        fileId = uploadData.file_id;
      } catch (err) {
        setLoading(false);
        setEntries((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            sessionId: sessionId || "",
            kind: "assistant_message",
            data: { content: `Error uploading image: ${err instanceof Error ? err.message : "Unknown error"}` },
            createdAt: new Date().toISOString(),
          },
        ]);
        return;
      }
      clearPendingFile();
    }

    const wsMessage = { content: text || "", ...(fileId ? { file_id: fileId } : {}) };

    if (!sessionId) {
      // No session yet — create one, then navigate (which triggers WS connection)
      try {
        const res = await fetch(`${API_BASE}/sessions`, { method: "POST" });
        if (!res.ok) throw new Error(`Failed to create session: ${res.status}`);
        const data = await res.json();
        pendingMessageRef.current = wsMessage;
        navigate(`/chat/${data.session_id}`, { replace: true });
      } catch (err) {
        setLoading(false);
        setEntries((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            sessionId: "",
            kind: "assistant_message",
            data: { content: `Error: ${err instanceof Error ? err.message : "Unknown error"}` },
            createdAt: new Date().toISOString(),
          },
        ]);
      }
    } else {
      // Session exists — send via WebSocket
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(wsMessage));
      } else {
        setLoading(false);
        setEntries((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            sessionId,
            kind: "assistant_message",
            data: { content: "Error: Connection lost. Please refresh the page." },
            createdAt: new Date().toISOString(),
          },
        ]);
      }
    }
  };

  return (
    <div className="app">
      <header className="header">
        <button
          className="new-chat-btn"
          onClick={() => {
            wsRef.current?.close();
            setEntries([]);
            setInput("");
            setLoading(false);
            clearPendingFile();
            navigate("/");
          }}
          aria-label="New chat"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
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
          <div className="empty-state">Send a photo of a parking sign to get started</div>
        )}
        {visibleEntries.map((entry) =>
          isMessageEntry(entry.kind) ? (
            <MessageBubble key={entry.id} entry={entry} />
          ) : (
            <EventCard key={entry.id} entry={entry} resultEntry={getResultEntry(entry)} />
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
          <Paperclip size={20} />
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
