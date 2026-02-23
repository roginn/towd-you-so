import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { X, Plus } from "lucide-react";

interface Session {
  id: string;
  started_at: string;
}

interface SessionSidebarProps {
  open: boolean;
  onClose: () => void;
  currentSessionId: string | undefined;
  onNewChat: () => void;
}

const API_BASE = "/api";

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function SessionSidebar({ open, onClose, currentSessionId, onNewChat }: SessionSidebarProps) {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/sessions`);
        if (res.ok) setSessions(await res.json());
      } catch {
        // ignore
      }
    })();
  }, [open]);

  return (
    <>
      <div className={`sidebar-overlay${open ? " visible" : ""}`} onClick={onClose} />
      <div className={`sidebar${open ? " open" : ""}`}>
        <div className="sidebar-header">
          <span className="sidebar-title">Sessions</span>
          <button className="sidebar-close" onClick={onClose} aria-label="Close sidebar">
            <X size={20} />
          </button>
        </div>
        <button
          className="sidebar-new-chat"
          onClick={() => {
            onNewChat();
            onClose();
          }}
        >
          <Plus size={16} />
          New Chat
        </button>
        <div className="sidebar-list">
          {sessions.map((s) => (
            <button
              key={s.id}
              className={`sidebar-item${s.id === currentSessionId ? " active" : ""}`}
              onClick={() => {
                navigate(`/chat/${s.id}`);
                onClose();
              }}
            >
              {formatTime(s.started_at)}
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
