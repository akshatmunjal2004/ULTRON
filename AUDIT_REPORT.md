# ULTRON AI Agent — Audit & Refactoring Report

This documents the state of the project as received, what was wrong, and what was
changed to make it production-ready. It is organised to match the phases in the
brief.

---

## Summary

The project was two half-finished builds sharing one folder. The git history
tells the story:

```
31bfa8d  Voice: offline Vosk recognition, hands-free wake word
9419c9f  Frontend: ULTRON orb UI with hands-free wake-word continuous voice
8c917f0  ULTRON AI Agent: FastAPI backend + React frontend
```

Each pass left the previous pass's files behind without deleting them. The
result: a chat UI and an orb UI in the same tree, two speech engines wired in
parallel, a 41 MB model committed into the repo, and a README describing
features the code did not implement.

The backend logic was sound in the small but wrong in the structure: everything
was flat, tools were defined twice, errors returned HTTP 200, and the one route
that ran Python had no authentication.

Both halves have been rebuilt. The backend now has 40 passing tests and a clean
`ruff` run; the frontend builds and lints clean, and its custom WAV and SSE code
is verified against the backend's actual validators.

---

## Phase 1 — Audit

### Architecture

| Area | Received | Assessment |
| --- | --- | --- |
| Backend layout | flat: `main.py`, `agent.py`, `models.py`, `database.py`, `routers/`, `tools/` | no separation of API / service / data layers |
| Frontend layout | `components/`, `hooks/`, `services/` | ~40% of files imported by nothing |
| Database | single `memory` table | conversations never persisted |
| API | unversioned, mixed response shapes | errors returned 200 with a body flag |
| Config | plain class reading `os.getenv` | no validation, `CORS=*` default |
| Voice | Web Speech in `App.jsx`, Vosk in an orphan hook | two engines, one unused |

### What was good

- Tool implementations were individually reasonable (workspace confinement was
  attempted, code execution had a timeout, memory used an upsert).
- The Web Speech recognition approach (`continuous = false`, finalize on pause)
  was the right call and was kept.
- The orb UI concept was distinctive and worth preserving.

### What was broken

1. **The agent had no memory between turns.** `App.jsx` called
   `sendChat(commandText)` and never passed history; the backend's `history`
   field was always `null`. Every message started from a blank slate.
2. **Unauthenticated remote code execution.** `POST /execute` accepted
   `{"tool": "code_runner", "args": {"code": "..."}}` with no auth, and
   `code_runner` shelled out to `sys.executable`. With `CORS_ORIGINS=*`, any web
   page could run code on the host.
3. **`open_url` opened tabs on the server.** It called `webbrowser.open()` in the
   backend process — useless to the user and a denial-of-service vector.
4. **Weak path containment.** `file_ops` used `str.startswith()`, so a sibling
   directory `workspace-notes` passed a check against `workspace`, and symlinks
   were followed out of the sandbox.
5. **Dead frontend.** `ChatUI`, `CommandBar`, `Sidebar`, `StatusIndicator`,
   `Loader`, `VoiceVisualizer`, `useAgent.js`, `useVosk.js` — none imported by
   the rendered app. Several referenced Tailwind classes (`ultron-border`,
   `ultron-accent2`) that did not exist in the config, and `useAgent.js`
   imported `{ api }` from a module that never exported it.
6. **A 41 MB Vosk model committed to the repo.** `.gitignore` excluded it, yet it
   shipped in the archive.
7. **README was fiction on three points:** a wake word (no such code), Vosk
   offline recognition (code used Web Speech), and `cp .env.example .env` (the
   example had been deleted; the real `.env` with a live key was present).

### What was incomplete

- No conversation persistence, logging module, request IDs, rate limiting,
  input-length validation, API versioning, health/readiness split, or tests.
- `@app.on_event("startup")` — deprecated in current FastAPI.
- `Agent()` constructed at import time, so importing a router required a key.

### Secret exposure

`backend/.env` contained a live `gsk_...` Groq key. It was never tracked by git
(only `.env.example` is tracked), but it travelled inside the shared archive and
must be rotated.

---

## Phase 2 — Removals

Deleted as dead or superseded:

- Components: `ChatUI`, `CommandBar`, `Sidebar`, `StatusIndicator`, `Loader`,
  `VoiceVisualizer`, plus the old `StatusPanel`, `CommandLog`, `AssistantResponse`,
  `UltronSphere` (replaced by cleaner equivalents).
- Hooks: `useAgent.js`, `useVosk.js`, old `useSpeechRecognition.js`.
- Assets: the Vosk model tarball, `public/models/` and its instructions.
- Dependency: `vosk-browser`.
- Backend: the flat `agent.py`, `models.py`, `database.py`, `config.py`,
  `routers/` — folded into the layered `app/` package.

---

## Phase 3 — Repairs

| Bug | Fix |
| --- | --- |
| Agent amnesia | history now loaded from the DB per `conversation_id`; server history overrides client |
| Unauthenticated RCE | `code_runner` off by default, auth-gated, resource-capped |
| Server-side `open_url` | returns a validated link for the frontend to open; blocks internal hosts |
| Path escape in `file_ops` | `Path.resolve()` + `is_relative_to()`; rejects `..`, absolute paths, symlink escapes |
| Errors as HTTP 200 | one JSON envelope with correct status codes and a request id |
| Missing validation | Pydantic length/shape limits on every input |
| Deprecated startup hook | lifespan context manager |
| Import-time client | agent and Groq clients created lazily via dependencies |
| Broken Tailwind classes | one complete token system; every class a component uses is declared |

Bugs found during testing and fixed: Pydantic validation errors weren't
JSON-serializable (broke the 422 handler); `os.setsid()` in `preexec_fn` clashed
with `start_new_session=True`; `setrlimit` on unsupported limits aborted spawns
in containers; the deprecated `HTTP_422` constant emitted warnings.

---

## Phase 4 — Structure

```
backend/app/
  core/        config, logging, errors, security
  db/          schema.sql, session, init, repositories/
  schemas/     pydantic contracts
  services/    groq_client, agent_service, transcription_service
  tools/       base + one file per tool + registry
  prompts/     system prompts
  middleware/  request context, rate limit
  api/v1/      endpoints/ + router + deps

frontend/src/
  api/         client, endpoints
  context/     AgentContext, ToastContext
  hooks/       useWebSpeech, useSpeechSynthesis, useAudioRecorder
  components/  orb, panels, layout, boundary, settings, toasts
  pages/       Assistant, Conversations, Memory
  utils/       format, browser
```

---

## Phases 5–10 — Improvements by area

**Backend (5).** Dependency-injected connections and services, Pydantic response
models on every route, a single error-handler set, structured logging with
per-request IDs, versioned `/api/v1`, async where it earns its keep (streaming,
uploads), sync-in-threadpool elsewhere.

**Frontend (6).** One API client that unwraps the error envelope and parses SSE;
typed endpoint wrappers; loading/empty/error states on every page; an error
boundary; toast notifications; router with three pages; code-split bundle;
keyboard focus rings; `prefers-reduced-motion` honoured throughout; a typed
fallback so the app is never voice-only.

**Database (7).** Four normalised tables (`memory`, `conversations`, `messages`,
`tool_calls`) with foreign keys and `ON DELETE CASCADE`, indexes on the columns
actually queried, WAL mode with a busy timeout, and an `updated_at` trigger.

**REST (8).** Resource-oriented paths, correct verbs (PUT for the idempotent
memory upsert, DELETE returning a result body), consistent JSON, pagination on
list endpoints, `q` filtering on memory.

**Groq (9).** One shared client, bounded retries with jittered backoff, a
`retry-after` honoured on 429, provider exceptions mapped to a clean upstream
error, prompts moved to `prompts/`, tool-result truncation, streaming support.

**Voice (10).** Browser path uses the Web Speech API with auto-restart between
phrases. Where that API is absent (Firefox, Safari), the frontend records audio,
encodes 16 kHz mono PCM WAV in the browser, and posts it to `/voice/transcribe`,
which uses Groq Whisper via Python `SpeechRecognition` (same key, no extra
service) with a Google Web Speech fallback.

---

## Phases 11–12 — Security & performance

**Security.** API-key auth on write/execute routes; per-IP rate limiting;
parameterised SQL with escaped LIKE wildcards; path containment; URL validation
blocking internal addresses; code execution off by default and capped; a
startup check that refuses to boot a misconfigured production instance;
credentials-less CORS with an explicit origin list.

**Performance.** Connection-per-unit-of-work with WAL; the model is shown only
enabled tools, cutting wasted round-trips; streaming so speech starts before
generation ends; debounced memory search; code-split frontend chunks
(react / motion / app); a lean particle count in the background.

---

## Phases 13–17 — Production readiness, gaps, quality, deliverables

Included: `requirements.txt`, `requirements-dev.txt`, `package.json`, both
`.env.example` files, a root `.gitignore` that also excludes WAL sidecars, a
README with setup / architecture / security / API reference / deployment, run
scripts, and interactive `/docs`.

Added features: health and readiness endpoints, a config module, an error
boundary, toasts, a reusable modal, an API wrapper, centralised error types, a
logger, a global exception handler, and validation on every input.

Code quality: `ruff` clean, PEP 8, type hints throughout the backend; ESLint
clean with the React Hooks plugin; small modules with one responsibility each.

### Verification performed

- Backend: 40 tests pass; `ruff` clean; real uvicorn boot with every route
  exercised and the full OpenAPI surface confirmed.
- Frontend: `npm run build` succeeds with split chunks; `npm run lint` clean;
  built `dist/` served with assets loading and SPA fallback working.
- Cross-boundary: the browser WAV encoder produces bytes that pass the backend's
  real `_validate_wav` and load into `SpeechRecognition`; the SSE parser
  reassembles tokens correctly across split chunk boundaries.

---

## Action required of you

1. **Rotate the Groq key** that was in the archived `.env`
   (<https://console.groq.com/keys>). It never entered git history, but it left
   your machine inside the tar.
2. In production, set `API_KEY`, real `CORS_ORIGINS`, and keep
   `ENABLE_CODE_EXECUTION=false` unless you run snippets in a container. The app
   will refuse to start otherwise.
