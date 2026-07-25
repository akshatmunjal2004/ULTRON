# ULTRON AI Agent

A voice-driven AI agent. A FastAPI backend gives a Groq-hosted model a small set
of tools it can call — web search, Python execution, workspace file access,
long-term memory, links and system info — and a React frontend wraps it in a
hands-free orb interface with a full transcript, conversation history and a
memory manager.

```
┌─────────────────────────┐        REST + SSE        ┌──────────────────────────┐
│  React + Vite frontend  │  ───────────────────────▶│   FastAPI backend        │
│  · orb / voice loop     │                          │   · agent + tool loop    │
│  · history + memory UI  │                          │   · Groq client          │
│  · Web Speech / recorder│◀───────────────────────  │   · SQLite (WAL)         │
└─────────────────────────┘        JSON / stream      └──────────────────────────┘
                                                             │
                                                     ┌───────┴────────┐
                                                     │  Groq API      │
                                                     │  chat + Whisper│
                                                     └────────────────┘
```

## Quick start

Two terminals. The backend first.

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then paste your GROQ_API_KEY
python run.py                     # http://localhost:8000, docs at /docs
```

Get a free Groq key at <https://console.groq.com/keys>.

Then the frontend.

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173 — open in Chrome for voice
```

The dev server proxies `/api` to `http://localhost:8000`, so the two run on
separate ports with no CORS setup. Open the app, click **Start listening**, and
speak. On Chrome and Edge it uses the browser's Web Speech API; on other
browsers it records a clip and transcribes it server-side with Groq Whisper.

## What each part is for

**Backend** (`backend/app`)

| Folder | Responsibility |
| --- | --- |
| `core/` | config, logging, error types + handlers, API-key auth |
| `db/` | SQLite schema, connection scope, repositories (all SQL lives here) |
| `schemas/` | Pydantic request/response contracts |
| `services/` | Groq client (retries/backoff), the agent loop, transcription |
| `tools/` | one class per tool; schemas are generated from their Pydantic models |
| `prompts/` | prompt templates, kept out of code |
| `middleware/` | request id + timing, in-process rate limiter |
| `api/v1/` | thin HTTP endpoints wired through dependencies |

**Frontend** (`frontend/src`)

| Folder | Responsibility |
| --- | --- |
| `api/` | one HTTP client (error-envelope + SSE) and typed endpoint wrappers |
| `context/` | agent state (connection, conversation, send) and toasts |
| `hooks/` | Web Speech recognition, speech synthesis, WAV recorder |
| `components/` | orb, panels, layout, error boundary, settings |
| `pages/` | Assistant, Conversations, Memory |
| `utils/` | formatting and browser-capability checks |

## Tools

| Tool | What it does | Notes |
| --- | --- | --- |
| `web_search` | DuckDuckGo results | on by default |
| `memory_tool` | save / recall / forget facts | writes to SQLite |
| `system_info` | date, time, OS, resource usage | — |
| `file_ops` | read / write / list / delete in the workspace | path-contained |
| `open_url` | returns a link for the browser to open | validated, no internal hosts |
| `code_runner` | runs a Python snippet | **off by default** — see Security |

The model only sees tools that are enabled, so it never proposes a call that is
guaranteed to fail. Each tool declares one Pydantic `Params` model; the schema
the model reads and the validation the server applies are both derived from it.

## Security

Read this before deploying anything.

- **`code_runner` executes model-generated Python.** It is disabled unless you
  set `ENABLE_CODE_EXECUTION=true`, the REST route that reaches it requires the
  API key, and it runs with CPU/memory/file/process limits in a throwaway
  directory. Those raise the cost of an accident; they are **not a sandbox**.
  For anything internet-facing, run snippets in a container or microVM instead.
- **Set `API_KEY` in production.** Write, delete and execute routes then require
  the `X-API-Key` header; reads stay open. Blank means auth off, which is fine
  for local use only.
- **Never set `CORS_ORIGINS=*` in production.** List your real origins.
- The app fails startup in `ENV=production` if any of the above is misconfigured
  (see `Settings.check_runtime_requirements`).
- A per-IP rate limiter guards every route except health. Behind more than one
  worker, move it to Redis.
- **Rotate any key that has ever been committed or shared**, including in an
  archive. `.env` is gitignored, but that only helps if the key never left.

## API reference

Base path `‎/api/v1`. Full interactive docs at `/docs` when not in production.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | – | liveness |
| GET | `/ready` | – | readiness (db, llm, enabled tools) |
| POST | `/chat` | – | send a message, get a full reply |
| POST | `/chat/stream` | – | send a message, stream tokens (SSE) |
| GET | `/conversations` | – | list threads |
| GET | `/conversations/{id}` | – | read one thread |
| DELETE | `/conversations/{id}` | key | delete a thread |
| GET | `/memory` | – | list / search facts |
| GET | `/memory/{key}` | – | read one fact |
| PUT | `/memory` | key | create or update a fact |
| DELETE | `/memory/{key}` | key | delete a fact |
| GET | `/tools` | – | list tools and their schemas |
| POST | `/tools/execute` | key | run a tool directly |
| GET | `/voice/capabilities` | – | what the server can transcribe |
| POST | `/voice/transcribe` | – | transcribe a WAV upload |

Every error has the same shape:

```json
{ "error": { "code": "not_found", "message": "…", "details": {} }, "request_id": "…" }
```

## Testing and linting

```bash
# backend
cd backend
pip install -r requirements-dev.txt
pytest                 # 40 tests
ruff check .

# frontend
cd frontend
npm run build          # type-free but catches import/JSX errors
npm run lint
```

## Deploying

**Backend** — behind a process manager, not `run.py`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

Set `ENV=production`, a strong `API_KEY`, real `CORS_ORIGINS`, and leave
`ENABLE_CODE_EXECUTION=false` unless you have containerised it. SQLite is fine
for a single node; for horizontal scale, move the DB and the rate limiter to
shared services.

**Frontend** — `npm run build` emits static files in `frontend/dist`. Serve them
from any static host and set `VITE_API_URL` to the backend's public origin at
build time.

## Configuration

Every setting and its default is documented in `backend/.env.example` and
`frontend/.env.example`. Nothing reads environment variables outside
`app/core/config.py`.
