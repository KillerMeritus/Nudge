# Nudge

> Privacy-first desktop productivity app — Pomodoro timer, task manager, and AI-powered daily summaries. Your data never leaves your device.

Built with **Tauri + React** (frontend) and **Python FastAPI** (backend). macOS and Windows.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Node.js | 18+ | https://nodejs.org |
| npm | 9+ | bundled with Node |
| Python | 3.11+ | https://python.org |
| Rust + Cargo | stable | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |

---

## Project Structure

```
nudge/
├── src/                  ← React frontend (FE-1)
│   ├── api/client.js     ← all API calls (toggle USE_MOCKS here)
│   ├── components/       ← Timer, Tasks, Summary, Settings
│   └── styles/global.css
│
├── src-tauri/            ← Tauri desktop shell (FE-2)
│   ├── src/main.rs
│   └── tauri.conf.json
│
├── backend/              ← FastAPI server (BE-1)
│   ├── main.py           ← entry point: uvicorn backend.main:app
│   ├── routers/          ← health, tasks, timer, summary, settings, activity
│   ├── storage/          ← task_store.py, settings_store.py (JSON files)
│   └── data/             ← tasks.json, settings.json (gitignored)
│
├── scraper/              ← Python activity monitor (BE-2)
│   ├── main.py           ← entry point: python3 scraper/main.py
│   ├── mac_scraper.py    ← pyobjc (macOS)
│   ├── windows_scraper.py← pywin32 (Windows)
│   ├── idle_detector.py
│   ├── whitelist.py
│   └── data/             ← current_activity.json, daily_log.json (gitignored)
│
├── API_CONTRACT.md       ← frozen — all 4 agree before changing
└── README.md
```

---

## Running Locally

Each part runs as a separate process. Open **4 terminal windows**.

### 1 — FastAPI Backend (BE-1)

```bash
# First time only — create virtual env and install deps
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run (from project root)
cd ..
source backend/.venv/bin/activate
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8080 --reload
```

Verify: http://127.0.0.1:8080/health → `{"status": "ok"}`  
API docs: http://127.0.0.1:8080/docs

---

### 2 — Activity Scraper (BE-2)

> **macOS only (current):** Requires Accessibility permissions. Go to System Settings → Privacy & Security → Accessibility → add Terminal (or your IDE).

```bash
# First time only — install macOS deps
pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz

# Run (from project root)
python3 -m scraper.main
```

The scraper writes to `scraper/data/current_activity.json` every 5 seconds.

---

### 3 — Tauri Desktop App (FE-1 + FE-2)

```bash
# First time only — install Node deps
npm install

# Run (starts Vite dev server + Tauri window)
npm run tauri dev
```

> The first `tauri dev` run will compile Rust and take 2–5 minutes. Subsequent runs are fast.

---

### 4 — React Frontend Standalone (FE-1 only, no Tauri window)

If you just want to work on the React UI without Tauri:

```bash
npm run dev
# Open http://localhost:5173
```

API calls use mock data by default (`USE_MOCKS = true` in `src/api/client.js`).  
Flip `USE_MOCKS = false` once the FastAPI server is running.

---

## One-Command Startup (after first-time setup)

```bash
# Terminal 1 — Backend
source backend/.venv/bin/activate && python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8080 --reload

# Terminal 2 — Scraper
python3 -m scraper.main

# Terminal 3 — App
npm run tauri dev
```

---

## Development Workflow

### Branches

| Person | Branch prefix | Owns |
|--------|--------------|------|
| FE-1 | `fe1/` | `src/` |
| FE-2 | `fe2/` | `src-tauri/` |
| BE-1 | `be1/` | `backend/` |
| BE-2 | `be2/` | `scraper/` |

- **Never commit to `main` directly** — always open a PR
- **`API_CONTRACT.md` is frozen** — all 4 agree before any change
- FE-1: keep `USE_MOCKS = true` until BE-1 confirms the server is stable

### Key files

- `src/api/client.js` — all frontend ↔ backend communication
- `backend/data/settings.json` — add your Gemini API key here (Settings tab in app)
- `API_CONTRACT.md` — the source of truth for all request/response shapes

---

## Phase 1 Features

- ✅ Pomodoro timer (focus, short break, long break)
- ✅ Task CRUD (title, description, priority, tags, estimated time, recurring)
- ✅ Activity monitoring (window title every 5s)
- ✅ Daily summary via Gemini API (add key in Settings)
- ✅ Settings persistence

## Phase 2 (post-hackathon)

- Local LLM via Ollama (Gemma)
- WebSocket real-time distraction alerts
- SQLite database
- Full UI-level scraping (Accessibility API depth 8)
- Notion integration

---

## API Reference

See [API_CONTRACT.md](./API_CONTRACT.md) for all endpoints, request bodies, and response shapes.

Interactive docs available at http://127.0.0.1:8080/docs when the server is running.
