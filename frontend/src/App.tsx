import { useState, useRef, useEffect, useCallback, FormEvent } from "react";
import { useParams, useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { Entry, isMessageEntry } from "./types";
import { buildResultByCallId, visibleEntries, getResultEntry } from "./entries";
import { MessageBubble } from "./components/MessageBubble";
import { EventCard } from "./components/EventCard";
import { Paperclip, Settings, X } from "lucide-react";

interface Memory {
  id: string;
  content: string;
  created_at: string;
}

const API_BASE = "/api";
const WS_BASE = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`;

function App() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [entries, setEntries] = useState<Entry[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);
  const [simDateTime, setSimDateTime] = useState(() => {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
  });
  const [overrideDateTime, setOverrideDateTime] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [pendingFile, setPendingFile] = useState<{ file: File; preview: string } | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const dragCounterRef = useRef(0);
  const [streamingReasoning, setStreamingReasoning] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingMessageRef = useRef<{ content: string; file_id?: string } | null>(null);

  // Send datetime override to backend
  const sendDateTimeOverride = useCallback(async (dt: string | null) => {
    try {
      const res = await fetch(`${API_BASE}/settings/datetime-override`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ datetime: dt }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setToast({
        message: dt ? `Override set: ${dt.replace("T", " ")}` : "Override cleared",
        type: "success",
      });
    } catch {
      setToast({ message: "Failed to set datetime override", type: "error" });
    }
  }, []);

  // Fetch memories from backend
  const fetchMemories = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/memories`);
      if (res.ok) setMemories(await res.json());
    } catch {
      // ignore
    }
  }, []);

  // Load memories on mount
  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  const deleteMemory = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/memories/${id}`, { method: "DELETE" });
      if (res.ok) setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch {
      // ignore
    }
  };

  // Auto-dismiss toast
  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 2500);
    return () => clearTimeout(id);
  }, [toast]);

  // Sync simDateTime changes when override is active
  const prevSimRef = useRef(simDateTime);
  useEffect(() => {
    if (prevSimRef.current !== simDateTime && overrideDateTime) {
      sendDateTimeOverride(simDateTime);
    }
    prevSimRef.current = simDateTime;
  }, [simDateTime, overrideDateTime, sendDateTimeOverride]);

  // Scroll to bottom when entries or streaming state change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, debugMode, streamingReasoning, streamingContent]);

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

        if (msg.type === "reasoning_delta") {
          setStreamingReasoning((prev) => (prev ?? "") + msg.text);
        }

        if (msg.type === "content_delta") {
          setStreamingContent((prev) => (prev ?? "") + msg.text);
        }

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
          // Clear streaming buffers when finalized entries arrive
          if (entry.kind === "reasoning") {
            setStreamingReasoning(null);
          }
          if (entry.kind === "assistant_message") {
            setStreamingContent(null);
          }
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
          setStreamingReasoning(null);
          setStreamingContent(null);
          setLoading(false);
          fetchMemories();
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
      };

      ws.onerror = () => {
        setLoading(false);
      };
    },
    [fetchMemories]
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
  const resultByCallId = buildResultByCallId(entries);
  const visible = visibleEntries(entries, debugMode);

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

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current++;
    if (e.dataTransfer.types.includes("Files")) {
      setDragOver(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) {
      setDragOver(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    dragCounterRef.current = 0;
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("image/")) {
      clearPendingFile();
      setPendingFile({ file, preview: URL.createObjectURL(file) });
    }
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
    <div
      className="app"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
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
            setTimeout(() => inputRef.current?.focus(), 0);
          }}
          aria-label="New chat"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
        <h1 onClick={() => {
          wsRef.current?.close();
          setEntries([]);
          setInput("");
          setLoading(false);
          clearPendingFile();
          navigate("/");
        }} style={{ cursor: "pointer" }}>Tow'd You So</h1>
        <button
          className="config-btn"
          onClick={() => setConfigOpen((o) => !o)}
          aria-label="Configuration"
        >
          <Settings size={20} />
        </button>
      </header>
      <div className={`config-panel${configOpen ? " open" : ""}`}>
        <div className="config-row">
          <span className="config-label">Debug</span>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={debugMode}
              onChange={(e) => setDebugMode(e.target.checked)}
            />
            <span className="toggle-slider" />
          </label>
        </div>
        <div className="config-row">
          <span className="config-label">Sim. Date</span>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="datetime-local"
              className="config-datetime"
              value={simDateTime}
              onChange={(e) => setSimDateTime(e.target.value)}
            />
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={overrideDateTime}
                onChange={(e) => {
                  const on = e.target.checked;
                  setOverrideDateTime(on);
                  sendDateTimeOverride(on ? simDateTime : null);
                }}
              />
              <span className="toggle-slider" />
            </label>
          </div>
        </div>
        <div className="config-section-title">Memories</div>
        {memories.length === 0 ? (
          <div className="config-memories-placeholder">No memories yet</div>
        ) : (
          <div className="config-memories-list">
            {memories.map((m) => (
              <div key={m.id} className="config-memory-item">
                <span className="config-memory-text">{m.content}</span>
                <button
                  className="config-memory-delete"
                  onClick={() => deleteMemory(m.id)}
                  aria-label="Delete memory"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="messages">
        {entries.length === 0 && (
          <div className="empty-state">Send a photo of a parking sign to get started</div>
        )}
        {visible.map((entry) =>
          isMessageEntry(entry.kind) ? (
            <MessageBubble key={entry.id} entry={entry} />
          ) : (
            <EventCard key={entry.id} entry={entry} resultEntry={getResultEntry(entry, resultByCallId)} />
          )
        )}
        {debugMode && streamingReasoning && (
          <div className="event-card streaming">
            <div className="event-card-header">
              <span className="event-icon">{"\uD83E\uDDE0"}</span>
              <span className="event-label">Reasoning</span>
              <span className="streaming-indicator">{"\u25CF"}</span>
            </div>
            <pre className="event-card-body">{streamingReasoning}</pre>
          </div>
        )}
        {streamingContent ? (
          <div className="message assistant">
            <div className="bubble"><ReactMarkdown>{streamingContent}</ReactMarkdown></div>
          </div>
        ) : loading && (
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
          ref={inputRef}
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
      {toast && (
        <div className={`toast toast-${toast.type}`}>{toast.message}</div>
      )}
      {dragOver && (
        <div className="drop-overlay">
          <div className="drop-overlay-content">Drop image here</div>
        </div>
      )}
    </div>
  );
}

export default App;
