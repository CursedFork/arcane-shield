# Arcane Shield

A local desktop DM companion for D&D 5e. No cloud, no auth, no server — everything lives in a single SQLite file on your machine.

**Stack:** Tauri 2 · Rust · SQLite (rusqlite, bundled) · React + TypeScript + Vite

---

## Prerequisites

| Tool | Install |
|------|---------|
| Rust + Cargo | `winget install Rustlang.Rustup` (restart terminal after) |
| VS C++ Build Tools | `winget install Microsoft.VisualStudio.2022.BuildTools` |
| Node.js ≥ 18 | [nodejs.org](https://nodejs.org) or `winget install OpenJS.NodeJS` |

---

## Dev

```bash
cd arcane-shield
npm install
npm run tauri dev
```

Tauri will compile the Rust backend, start the Vite dev server, and open the app window. Hot-reload works for the React layer; Rust changes require a recompile (Tauri handles this automatically on save).

## Build (production)

```bash
npm run tauri build
```

Produces an installer in `src-tauri/target/release/bundle/`.

---

## Data

The SQLite database is stored at:
- **Windows:** `%APPDATA%\com.arcane.shield\arcane-shield.db`
- **macOS:** `~/Library/Application Support/com.arcane.shield/arcane-shield.db`

Tables: `players`, `magic_items`, `bestiary`, `mechanics`, `campaigns`, `notes`, `shops`, `party_items`, `saved_encounters`.

---

## Ingestion Pipeline (separate)

The `/ingestion` folder contains a standalone Python pipeline that converts PDFs and DOCX files (sourcebooks, homebrew docs) into structured JSON using markitdown + Claude API, then imports that JSON into the app's database.

See [ingestion/README.md](ingestion/README.md) for the two-step run instructions.

Quick import after running the pipeline:
1. Open Arcane Shield
2. *(Phase 2)* Use the Import button to point at the `json_output/` directory

---

## Architecture

All data mutations go through Rust Tauri commands (`src-tauri/src/commands/`). The React layer calls `invoke(...)` and renders results — it holds no source-of-truth state. Validation lives in Rust and returns readable error strings.

```
arcane-shield/
├── ingestion/          Python ingestion pipeline (standalone)
├── src/                React + TypeScript frontend
│   ├── components/     Sidebar, shared UI
│   └── pages/          One file per route
└── src-tauri/          Rust backend
    └── src/
        ├── lib.rs       App setup, Tauri builder, state
        ├── db.rs        SQLite migrations
        ├── models.rs    Serde structs for every schema
        └── commands/    One file per domain (players, items, ...)
```
