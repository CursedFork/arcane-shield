<div align="center">

# ⚔️ Arcane Shield

### A fast, fully‑offline Dungeon Master's reference & screen tool for D&D 5e

*Build your own DM screen, run combat, and look up rules, monsters, and loot — all from one local desktop app. No server, no build step, no internet required.*

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-1f6aa5)
![SQLite](https://img.shields.io/badge/Storage-SQLite-003B57?logo=sqlite&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

---

## ✨ Overview

**Arcane Shield** is a desktop companion for running tabletop D&D sessions. Everything a DM juggles mid‑game — initiative, monster stat blocks, magic items, house rules, shops, party loot, and session notes — lives in one keyboard‑and‑mouse‑friendly app that opens instantly and works completely offline.

The headline feature is the **DM Shield**: a free‑form, drag‑and‑drop dashboard where you arrange live panels (initiative tracker, searchable mechanics, quick notes, bestiary, and more) into a custom layout that fits the way *you* run the table.

> 💡 All data is stored in a single local SQLite database. Nothing leaves your machine.

---

## 🖼️ Screenshots

<!--
Drop your screenshots into a docs/ folder and uncomment the lines below.
Recommended shots: the DM Shield with a few panels, the Initiative Tracker,
and the Bestiary with a stat block open.

| DM Shield | Initiative Tracker |
|-----------|--------------------|
| ![DM Shield](docs/dm-shield.png) | ![Initiative](docs/initiative.png) |
-->

*Screenshots coming soon — clone it and try it in under a minute (see [Getting Started](#-getting-started)).*

---

## 🎲 Features

| Section | What it does |
|---------|--------------|
| 🛡️ **DM Shield** | Build custom dashboards from draggable, freely‑resizable panels. Each panel pulls **live** data from any other section. Multiple tabs, prebuilt column layouts, and one‑click starter templates ("Combat Screen", "Session Prep"). |
| ⚔️ **Initiative Tracker** | Full combat manager: HP damage/heal, AC, 15 standard 5e conditions, a built‑in dice roller, round/turn tracking, save & load encounters, load players from the roster, and drop in monsters straight from the bestiary. |
| ☠️ **Bestiary** | Monster library with Markdown stat blocks. Filter by **Challenge Rating** and **monster type**. |
| ✦ **Magic Items** | Catalog with rarity color‑coding. Filter by **type**, **rarity**, **attunement**, and **tag**. |
| ⚙️ **Mechanics** | House rules & rules references rendered from Markdown. Filter by **campaign** and **category**. |
| 📖 **Campaigns** | Long‑form campaign/world notes with Markdown and tag filtering. |
| ✎ **Session Notes** | Quick‑add notes grouped by session. Filter by **session** or **date**. |
| ⚖️ **Shops & Loot** | Shop inventories, party loot by owner, and a party roster — each searchable and filterable. |
| ⬆️ **Bulk Import** | Import a whole folder of CSVs at once; the table is auto‑detected from the column headers. |

**Throughout the app:**

- 📝 **Markdown rendering** — headers, bold/italic, code blocks, lists, and rules render cleanly in stat blocks, mechanics, and notes.
- 🎯 **Live filters on every tab** — dropdowns auto‑populate from your own data.
- 🎲 **Dice roller** — supports `1d20+5`, `2d6`, advantage/disadvantage (`1d20adv` / `1d20dis`), and more.
- 💾 **CSV import & export** — move data in and out of any section.
- ⚡ **Instant launch** — no console window, custom taskbar icon, no compilation.

---

## 🛠️ Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | **Python 3.10+** | Zero‑build, cross‑platform, batteries‑included stdlib |
| UI | **CustomTkinter** | Modern dark‑themed widgets on top of Tk |
| Storage | **SQLite** (stdlib `sqlite3`) | Single‑file, zero‑config, fully local; WAL mode + foreign keys |
| Layout engine | **tkinter `Canvas`** | Absolute positioning powers the free‑form DM Shield |
| Icon pipeline | **Pillow** | PNG → ICO conversion for the app/taskbar icon |
| Data exchange | **csv** (stdlib) | Import/export with header‑based table detection |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10 or newer** ([download](https://www.python.org/downloads/)) — make sure "Add Python to PATH" is checked during install.
- Windows is the primary target (custom icon + no‑console launch), but the app also runs on macOS/Linux via `python main.py`.

### Quick start (Windows)

```bash
git clone https://github.com/CursedFork/arcane-shield.git
cd arcane-shield
run.bat
```

`run.bat` installs the two dependencies and launches the app with no console window. That's it.

### Quick start (any platform / manual)

```bash
git clone https://github.com/CursedFork/arcane-shield.git
cd arcane-shield
pip install -r requirements.txt
python main.py
```

The database is created automatically on first run — no setup required.

---

## 📂 Where your data lives

Arcane Shield keeps everything in one SQLite file:

```
%APPDATA%\ArcaneShield\arcane-shield.db      (Windows)
~/ArcaneShield/arcane-shield.db              (Linux/macOS)
```

To **back up** your campaign, just copy that file. To **start fresh**, delete it (the app recreates it on launch).

---

## 📥 Importing your own data (CSV)

Use the **Bulk Import** tab to load a folder of CSV files at once. The target table is detected automatically from the column headers — no manual mapping needed. Each section also exports to CSV, so an export is a perfect import template.

<details>
<summary><b>CSV column reference (click to expand)</b></summary>

| Section | Required / key columns |
|---------|------------------------|
| **Magic Items** | `name, item_type, rarity, requires_attunement, attunement_requirement, description, mechanical_effect, charges, source_campaign, tags` |
| **Bestiary** | `name, ac, max_hp, initiative_mod, cr, statblock_md, tags` |
| **Mechanics** | `title, body_md, campaign, tags` |
| **Campaigns** | `title, body_md, tags` |
| **Session Notes** | `session_label, note_date, body` |
| **Shops** | `shop_name, item_name, price, quantity, notes` |
| **Party Loot** | `item_name, owner, quantity, notes` |
| **Party Roster** | `player_name, character_name, ac, max_hp, initiative_mod, passive_perception, notes` |

`tags` columns accept a semicolon‑ or comma‑separated list (e.g. `Undead;Construct`). `*_md` columns accept Markdown.

</details>

---

## 🧱 Project Structure

```
arcane-shield/
├── main.py            # App window, sidebar nav, page routing
├── db.py              # SQLite schema, all CRUD, CSV import/export
├── dice.py            # Dice expression parser (NdM±K, adv/dis)
├── run.bat            # One‑click Windows launcher (no console window)
├── requirements.txt
└── pages/
    ├── dm_shield.py   # Free‑form drag/resize dashboard
    ├── initiative.py  # Combat & initiative tracker
    ├── bestiary.py    # Monsters + stat blocks
    ├── items.py       # Magic items
    ├── mechanics.py   # House rules / rules reference
    ├── campaigns.py   # Campaign & world notes
    ├── notes.py       # Session notes
    ├── shops.py       # Shops, party loot, roster
    ├── bulk_import.py # Folder CSV import
    └── md_widget.py   # Lightweight Markdown → tkinter renderer
```

---

## 🧠 Engineering Highlights

A few decisions worth calling out for anyone reading the source:

- **Pure Python, by design.** This project was rewritten from a Tauri (Rust + React/TypeScript) stack down to a single Python app to eliminate the build pipeline, the bundled web runtime, and a class of WebView drag‑and‑drop bugs. The result launches faster, ships smaller, and is far easier to hack on.
- **Free‑form layout on a canvas.** The DM Shield abandons grid/flow layout in favor of a `tkinter.Canvas` with absolutely‑positioned panel windows. Each panel owns its own `x, y, width, height`, so resizing one panel never disturbs another — the geometry persists to SQLite per panel.
- **A tiny Markdown renderer.** `md_widget.py` is a dependency‑free Markdown‑to‑Tk renderer (headers, emphasis, code, lists, rules) so stat blocks and rules read like documents, not raw text.
- **Header‑driven CSV detection.** Imports figure out which table a CSV belongs to from its columns first, falling back to the filename — so dropping in a folder of mixed exports "just works."

---

## 🗺️ Roadmap

- [ ] In‑app screenshots & a short demo GIF
- [ ] Dedicated **Spells** section (school / level / class filters)
- [ ] Theming options beyond the default dark palette
- [ ] Packaged executable (PyInstaller) for one‑download installs

---

## 📜 License

Released under the **MIT License** — see [`LICENSE`](LICENSE). Free to use, modify, and share.

---

<div align="center">

*Built for DMs who'd rather be running the game than alt‑tabbing through ten browser tabs.*

</div>
