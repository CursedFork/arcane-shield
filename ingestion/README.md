# Arcane Shield — Ingestion Pipeline

Converts PDF/DOCX source files (sourcebooks, campaign docs, homebrew PDFs) into structured JSON that the Arcane Shield desktop app can import into its SQLite database.

This is a **standalone Python pipeline**. It never runs inside the app.

## Prerequisites

- Python 3.10+
- An Anthropic API key

## Setup

```bash
cd ingestion
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Set your API key:

```bash
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Two-Step Run

### Step 1 — Convert source files to Markdown

```bash
python convert.py --input ./raw_docs --output ./markdown
```

- Recursively scans `raw_docs/` for `.pdf`, `.docx`, `.doc`, `.pptx`, `.xlsx`, `.html` files.
- Runs **markitdown** on each and writes a `.md` file to `markdown/`, preserving subdirectory structure.
- Exits with code 1 if any file fails conversion.

### Step 2 — Extract structured records with Claude

```bash
python parse_to_json.py --input ./markdown --output ./json_output
```

- Reads every `.md` file produced by Step 1.
- Calls `claude-sonnet-4-6` to extract records matching the Arcane Shield schemas.
- Writes one JSON file per record type to `json_output/`:

| File | Schema |
|------|--------|
| `magic_items.json` | Magic items (name, type, rarity, description, etc.) |
| `bestiary.json` | Monsters and NPCs (AC, HP, CR, stat block) |
| `mechanics.json` | Homebrew rules and mechanics (Markdown docs) |
| `campaigns.json` | Campaign writeups (Markdown docs) |

- Skips and logs any record that fails schema validation to `json_output/validation_errors.txt`.

---

## Importing into the App

Once Phase 1 of the app is built, use the in-app import function and point it at the `json_output/` directory. The Rust backend ingests each JSON file into the corresponding SQLite table.

---

## What gets extracted?

| Source content | Extracted as |
|----------------|-------------|
| Magic item descriptions | `magic_items` |
| Monster stat blocks | `bestiary` |
| Custom/homebrew rules | `mechanics` |
| Campaign lore, session recaps | `campaigns` |

Players, notes, shops, and party inventory are entered directly in the app (or imported via CSV after Phase 3).
