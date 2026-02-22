# Tow'd You So: AI Parking Sign Assistant - Requirements Document

# 1. Product Requirements

## 1.1 Core Functionality
- User submits a photo of a parking sign (camera capture or file upload) and optionally a text message (e.g., "Can I park here until 6pm?")
- The agent analyzes the sign using computer vision and responds with a clear **yes/no/conditional** answer about whether parking is allowed
- The agent should factor in the **current date and time** (or a user-specified time) when making its determination
- Responses should include a brief **explanation** of the sign's rules so the user understands *why*

## 1.2 Chat Interface
- Conversational UI: messages flow between user and agent in a familiar chat layout
- User can send **text**, **images** (photo/file upload), or **both** in a single message
- Agent responses appear as chat bubbles with markdown support for structured answers

## 1.3 Debug / Transparency Mode
- Toggleable debug mode that shows the agent's internal process as **event messages** in the chat stream
- Event types include:
  - 🔧 **Tool use** – e.g., "Calling OCR tool on uploaded image…"
  - 🧠 **Reasoning** – e.g., "Sign indicates no parking Mon–Fri 8am–6pm. Current time is Tuesday 3pm…"
  - 🤖 **Sub-agent delegation** – e.g., "Delegating to sign-parsing sub-agent…"
  - ✅ **Result** – e.g., "Determination complete"
- Events are visually distinct from user/agent chat messages (muted style, collapsible, or side-rail)

## 1.4 Responsive Design
- Fully usable on **desktop** (laptop browser) and **mobile** (phone browser)
- Mobile-first considerations: large tap targets for upload, camera capture button, readable text at small widths
- No native app required



# 2. Technical Requirements

## 2.1 Frontend — React App

| Aspect | Decision |
|---|---|
| Framework | React (Vite or Next.js static export) |
| Styling | Tailwind CSS |
| State management | React Context or Zustand (lightweight) |
| Responsive | Tailwind breakpoints, mobile-first layout |

### 2.1.1 Entry Model
```
EntryKind = "user_message" | "assistant_message" | "tool_call"
          | "tool_result" | "reasoning" | "sub_agent_call"
          | "sub_agent_result"

Entry {
  id: string
  sessionId: string
  kind: EntryKind
  data: object             // shape varies by kind (see §2.3.3)
  createdAt: ISO string
}
```

Entries with kind `user_message` or `assistant_message` render as chat bubbles. All other kinds render as debug event cards, visible only when debug mode is enabled.

### 2.1.2 Key Components
- `ChatWindow` – scrollable message list, auto-scroll on new messages
- `MessageBubble` – renders user, agent, and event messages with distinct styles
- `InputBar` – text input + file/image attach + send button; camera capture on mobile
- `DebugToggle` – switch to show/hide event messages


## 2.2 Backend — Python FastAPI

### 2.2.1 Project Structure

TBD! Not a final version. We still have to think about how to organize agents, tools and memory.

```
backend/
├── main.py                  # FastAPI app, endpoints, WebSocket handler
├── agent/
│   ├── orchestrator.py      # Main agent loop: receives input, delegates, returns answer
│   ├── sub_agents/          # Specialized sub-agents
│   │   └── sign_parser.py   # Parses sign text/rules from OCR output
│   └── prompts/             # System prompts and prompt templates
├── tools/
│   ├── read_parking_sign.py # Image-to-text (uses Roboflow API to detect the sign and OCR it)
│   ├── vision.py            # General purpose image description using a VLM
│   └── time_utils.py        # Current time / date helpers, timezone handling
├── memory/
│   ├── conversation.py      # Per-session conversation history
│   └── context.py           # Extracted parking rules context for the current sign
├── db/
│   ├── database.py          # DB connection / session factory
│   ├── models.py            # SQLAlchemy ORM models (Session, Entry)
│   └── repository.py        # CRUD helpers for sessions and entries
├── interface/
│   ├── models.py            # Pydantic models for all message types (shared contract)
│   └── events.py            # Event emission helpers (tool use, reasoning, etc.)
├── config.py                # API keys, model settings, feature flags
└── requirements.txt
```

### 2.2.2 Tool Execution Model

Tools receive **only** the explicit parameters the LLM provides in its `tool_calls` arguments — no implicit context. The worker is a dumb executor: it dispatches `tool_name` + `arguments` and writes the result.

- Tools must declare all required inputs in their function `parameters` schema so the LLM knows to supply them.
- The LLM is responsible for extracting values (e.g., `file_id` from the user message) and passing them as tool arguments.
- Sub-agents receive only the parameters they need (e.g., `uploaded_file_id`), not the full conversation history. This keeps sub-agent context small and focused.

**Tool naming convention:** Tools that delegate to a sub-agent (i.e., spawn an internal LLM loop) must be prefixed with `task_` (e.g., `task_read_parking_sign`). Leaf tools that perform a single operation (API call, DB query, etc.) use plain names (e.g., `ocr_parking_sign`, `get_current_time`). This makes it easy to distinguish orchestrator-level delegation from direct execution.

Example: `task_read_parking_sign` requires `{ file_id: string }`. The orchestrator's system prompt and user message annotation (`[User attached an image (file_id: ...)]`) give the LLM the information it needs to supply this argument.

### 2.2.3 Interface Models (Pydantic)
```python
class EntryKind(str, Enum):
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    REASONING = "reasoning"
    SUB_AGENT_CALL = "sub_agent_call"
    SUB_AGENT_RESULT = "sub_agent_result"

class Entry(BaseModel):
    id: str
    session_id: str
    kind: EntryKind
    data: dict                # shape varies by kind (see §2.3.3)
    created_at: datetime
```

## 2.3 Data Layer — Database

Sessions and entries are persisted in a relational database. A **Session** is a conversation context. An **Entry** is anything that happens inside a session — user messages, agent responses, tool calls, reasoning steps, sub-agent delegations — stored as a flat ordered list.

### 2.3.1 Schema

**Session**
| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Unique session identifier |
| `parent_id` | UUID (FK → Session.id, nullable) | Links a child session to its parent (sub-agent sessions) |
| `started_at` | datetime (UTC) | When the session was created |

**Entry**
| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Unique entry identifier |
| `session_id` | UUID (FK → Session.id) | The session this entry belongs to |
| `kind` | enum | One of the `EntryKind` values (see below) |
| `data` | JSONB | Payload — shape varies by `kind` |
| `created_at` | datetime (UTC) | Timestamp; provides natural ordering within the session |

### 2.3.2 Entry Kinds

| Kind | Category | Description |
|---|---|---|
| `user_message` | message | User's input to the agent |
| `assistant_message` | message | Agent's response visible to the user |
| `tool_call` | event | Agent invoked a tool |
| `tool_result` | event | A tool returned its result |
| `reasoning` | event | Agent's internal reasoning step |
| `sub_agent_call` | event | Agent delegated work to a sub-agent |
| `sub_agent_result` | event | A sub-agent returned its result |

**Category** is not stored — it's a conceptual grouping. "Message" entries are always visible in the chat UI. "Event" entries are only visible when debug mode is enabled.

### 2.3.3 Entry `data` Shapes

Each `kind` has a specific payload shape stored in the `data` JSONB column:

```
user_message     → { content: string, image_url?: string }
assistant_message→ { content: string }
tool_call        → { call_id: string, tool_name: string, arguments: object }
tool_result      → { call_id: string, result: any }
reasoning        → { content: string }
sub_agent_call   → { child_session_id: UUID, agent_name: string }
sub_agent_result → { child_session_id: UUID, result: any }
```

### 2.3.4 Example: A Real Conversation

```
Session { id: "s1", parent_id: null }

Entries (ordered by created_at):
───┬──────────────────┬──────────────────────────────────────────────────
 # │ kind             │ data (abbreviated)
───┼──────────────────┼──────────────────────────────────────────────────
 1 │ user_message     │ { content: "Can I park here?", image_url: "…" }
 2 │ tool_call        │ { call_id: "tc1", tool_name: "read_sign", … }
 3 │ tool_result      │ { call_id: "tc1", result: "No parking 8-6" }
 4 │ sub_agent_call   │ { child_session_id: "s2", agent_name: "parser" }
 5 │ sub_agent_result │ { child_session_id: "s2", result: { rules… } }
 6 │ reasoning        │ { content: "It's Tuesday 3pm, sign says…" }
 7 │ assistant_message│ { content: "**No**, you cannot park here…" }
───┴──────────────────┴──────────────────────────────────────────────────
```

The sub-agent's child session has its own entries:

```
Session { id: "s2", parent_id: "s1" }

Entries:
───┬──────────────────┬──────────────────────────────────────────────────
 # │ kind             │ data (abbreviated)
───┼──────────────────┼──────────────────────────────────────────────────
 1 │ user_message     │ { content: "Parse these sign rules: …" }
 2 │ reasoning        │ { content: "Extracting time windows…" }
 3 │ assistant_message│ { content: "{ weekday: 'Mon-Fri', … }" }
───┴──────────────────┴──────────────────────────────────────────────────
```

### 2.3.5 Sub-Agent Sessions

When the orchestrator delegates to a sub-agent:
1. A new **child Session** is created with `parent_id` pointing to the parent session.
2. A `sub_agent_call` entry is appended to the **parent** session, referencing the child session's ID.
3. The sub-agent runs within its own session, producing its own entries.
4. When complete, a `sub_agent_result` entry is appended to the **parent** session with the sub-agent's output.

The root session always has `parent_id = NULL`.

### 2.3.6 Conversation Replay

When building the LLM conversation context from a session's entries, entries map to LLM message roles:

| Entry kind | LLM role |
|---|---|
| `user_message` | `user` |
| `assistant_message` | `assistant` |
| `tool_call` | `assistant` (with `tool_calls` array) |
| `tool_result` | `tool` (with `tool_call_id`) |
| `reasoning` | excluded or summarised |
| `sub_agent_call` / `sub_agent_result` | excluded or summarised |

## 2.4 Client–Server Connection

- Chat messages & events: **WebSocket** — single persistent connection per session. Server pushes agent messages and debug events as they happen in real time.
- Image/file upload: **HTTP POST** `/api/upload` — multipart form upload returns a `file_id`. Client then references `file_id` in the WebSocket message.

### 2.4.1 Connection Flow
```
1. Client opens WebSocket → ws://host/ws/{session_id}
2. User attaches image → POST /api/upload → returns { file_id }
3. User sends message via WebSocket:
   { "content": "Can I park here now?", "file_id": "abc123" }
4. Server streams back entries via WebSocket:
   → { kind: "tool_call", data: { call_id: "tc1", tool_name: "read_sign", … } }
   → { kind: "tool_result", data: { call_id: "tc1", result: "No parking 8am–6pm…" } }
   → { kind: "reasoning", data: { content: "Sign says no parking 8am–6pm…" } }
   → { kind: "assistant_message", data: { content: "**Yes, you can park here.** …" } }
```

