<div align="center">

# ⚔️ Arcane Shield

### A fast, fully‑offline Dungeon Master's reference, compendium & screen tool for D&D 5e

*Run combat, build a custom DM screen, and look up spells, monsters, classes, rules, and loot — all from one local desktop app. No server, no build step, no internet required.*

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-1f6aa5)
![SQLite](https://img.shields.io/badge/Storage-SQLite-003B57?logo=sqlite&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

---

## ✨ Overview

**Arcane Shield** is a desktop companion for running tabletop D&D sessions. Everything a DM juggles mid‑game — initiative, monster stat blocks, spells, magic items, character options, house rules, shops, party loot, and session notes — lives in one keyboard‑and‑mouse‑friendly app that opens instantly and works completely offline.

It's two things at once:

- a **DM screen** — the **DM Shield**, a free‑form, drag‑and‑drop dashboard where you arrange live panels (initiative tracker, dice roller, searchable mechanics, quick notes, bestiary, and more) into a layout that fits the way *you* run the table; and
- a **searchable compendium** — spells, monsters, magic items, races/classes/subclasses/backgrounds/feats, conditions, skills, and languages, each in its own filterable tab.

> 💡 All data lives in a single local SQLite database. Nothing leaves your machine — and the app **backs itself up and self‑heals** if that file is ever corrupted.

> 🗡️ A player‑facing companion app, **Arcane Sword** (a character builder that reuses this app's schema and compendium data), is in development.

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

### Run the table

| Section | What it does |
|---------|--------------|
| 🛡️ **DM Shield** | Build custom dashboards from draggable, freely‑resizable panels, each pulling **live** data from any other section. Multiple tabs, prebuilt column layouts, one‑click starter templates ("Combat Screen", "Session Prep"), and a **top‑bar dice roller** (d2–d100, quantity, modifier, advantage/disadvantage, roll log). |
| ⚔️ **Initiative Tracker** | Full combat manager: HP damage/heal & temp HP, AC, the standard 5e conditions, a dice roller, round/turn tracking, save & load encounters, load players from the roster, and drop in monsters straight from the bestiary. **Shares one live encounter** with the DM Shield's initiative panel. |

### Compendium & reference

| Section | What it does |
|---------|--------------|
| ☠️ **Bestiary** | Monster library with Markdown stat blocks. Filter by **CR**, **monster type**, and **source** (official WotC books by name; everything else as *Third‑Party* or *Homebrew*). |
| ✨ **Spells** | Searchable spellbook. Filter by **level**, **school**, and **class**; full casting details + Markdown description. |
| ✦ **Magic Items** | Catalog with rarity color‑coding. Filter by **type**, **rarity**, **attunement**, and **tag**. |
| 🧙 **Character Options** | Races, Classes, Subclasses, Backgrounds, and Feats in sub‑tabs. Subclasses filter **by main class**; Feats filter by **source** (e.g. XPHB), **boon**, and **prerequisite**. |
| 🜸 **Conditions** | The standard 5e conditions as a quick reference (also feeds the initiative tracker). |
| 🎯 **Skill Checks** | The 18 skills with their governing ability and usage. |
| 🗣️ **Languages** | D&D languages (Standard / Exotic / Secret) with script and typical speakers. |
| ⚙️ **Mechanics** | House rules & rules references in Markdown. Filter by **campaign**, **category** (tags), and **group** (title prefix). |
| 📖 **Campaigns** & 🌍 **Setting Info** | Long‑form world/campaign notes and published‑setting lore, with Markdown and tag filtering. |
| ✎ **Session Notes** | Quick‑add notes grouped by session. Filter by **session** or **date**. |
| ⚖️ **Shops & Loot** | Shop inventories, party loot by owner, and a party roster — each searchable and filterable. |
| ⬆️ **Bulk Import** | Import a whole folder of CSVs at once (table auto‑detected from headers), plus a guarded **Erase All Data** reset. |

**Throughout the app:**

- 📝 **Markdown rendering** — headers, bold/italic, code, lists, and rules render cleanly in stat blocks, spells, mechanics, and notes.
- 🎯 **Live filters + one‑click reset on every tab** — dropdowns auto‑populate from your own data.
- 🎲 **Dice roller** — `1d20+5`, `2d6`, advantage/disadvantage (`1d20adv` / `1d20dis`), and more, plus the DM Shield's button roller.
- 💾 **CSV import & export** — move data in and out of any section.
- 🛟 **Self‑healing storage** — every launch snapshots a rotating backup; a corrupt database is quarantined and auto‑restored from the latest good copy.
- ⚡ **Instant launch** — no console window, custom taskbar icon, no compilation. Large lists render fast via a lightweight scrolling list widget.

---

## 🛠️ Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | **Python 3.10+** | Zero‑build, cross‑platform, batteries‑included stdlib |
| UI | **CustomTkinter** | Modern dark‑themed widgets on top of Tk |
| Storage | **SQLite** (stdlib `sqlite3`) | Single‑file, zero‑config, fully local; WAL mode + foreign keys, with integrity checks and rotating backups |
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

The database is created automatically on first run, seeded with the standard conditions, skills, and languages — no setup required.

---

## 📂 Where your data lives

Arcane Shield keeps everything in one SQLite file, plus a folder of rotating backups:

```
%APPDATA%\ArcaneShield\arcane-shield.db      (Windows)   ~/ArcaneShield/arcane-shield.db   (Linux/macOS)
%APPDATA%\ArcaneShield\backups\              (last 7 automatic snapshots)
```

To **back up** your campaign, copy the `.db` file. To **start fresh**, use **Bulk Import → Erase All Data**, or delete the file (the app recreates it on launch). If the database is ever corrupted, the app moves it aside and restores the newest healthy backup automatically.

---

## 📥 Importing your own data (CSV)

Use the **Bulk Import** tab to load a folder of CSV files at once. The target table is detected automatically from the column headers — no manual mapping needed. Each section also exports to CSV, so an export is a perfect import template.

<details>
<summary><b>CSV column reference (click to expand)</b></summary>

| Section | Required / key columns |
|---------|------------------------|
| **Magic Items** | `name, item_type, rarity, requires_attunement, attunement_requirement, description, mechanical_effect, charges, source_campaign, tags` |
| **Bestiary** | `name, ac, max_hp, initiative_mod, cr, statblock_md, tags, source` |
| **Spells** | `name, level, school, casting_time, range, components, duration, concentration, ritual, classes, description, source, tags` |
| **Character Options** | `category, name, parent, body_md, source, tags`  (category = race / class / subclass / background / feat) |
| **Mechanics** | `title, body_md, campaign, tags` |
| **Campaigns** | `title, body_md, tags` |
| **Setting Info** | `name, body_md, tags` |
| **Session Notes** | `session_label, note_date, body` |
| **Shops** | `shop_name, item_name, price, quantity, notes` |
| **Party Loot** | `item_name, owner, quantity, notes` |
| **Party Roster** | `player_name, character_name, ac, max_hp, initiative_mod, passive_perception, notes` |

`tags` columns accept a semicolon‑ or comma‑separated list (e.g. `Undead;Construct`). `*_md` / `description` / `body_md` columns accept Markdown. Conditions, skills, and languages are seeded automatically.

</details>

---

## 🧱 Project Structure

```
arcane-shield/
├── main.py            # App window, sidebar nav, page routing
├── db.py              # SQLite schema, all CRUD, CSV import/export, self-heal/backup
├── dice.py            # Dice expression parser (NdM±K, adv/dis)
├── run.bat            # One-click Windows launcher (no console window)
├── requirements.txt
└── pages/
    ├── dm_shield.py        # Free-form drag/resize dashboard + dice roller
    ├── initiative.py       # Combat & initiative tracker (shared live encounter)
    ├── bestiary.py         # Monsters + Markdown stat blocks
    ├── spells.py           # Spellbook
    ├── items.py            # Magic items
    ├── character_options.py# Races / Classes / Subclasses / Backgrounds / Feats
    ├── conditions.py       # 5e conditions reference
    ├── skills.py           # Skill checks reference
    ├── languages.py        # Languages reference
    ├── mechanics.py        # House rules / rules reference
    ├── campaigns.py        # Campaign & world notes
    ├── settings.py         # Published-setting lore
    ├── notes.py            # Session notes
    ├── shops.py            # Shops, party loot, roster
    ├── bulk_import.py      # Folder CSV import + Erase All Data
    ├── md_widget.py        # Lightweight Markdown → tkinter renderer
    └── ui_util.py          # Fast ScrollList + row helpers
```

---

## 🧠 Engineering Highlights

A few decisions worth calling out for anyone reading the source:

- **Pure Python, by design.** Rewritten from a Tauri (Rust + React/TypeScript) stack down to a single Python app to eliminate the build pipeline, the bundled web runtime, and a class of WebView drag‑and‑drop bugs. Launches faster, ships smaller, and is far easier to hack on.
- **Free‑form layout on a canvas.** The DM Shield uses a `tkinter.Canvas` with absolutely‑positioned panel windows. Each panel owns its own `x, y, width, height`, so resizing one never disturbs another — geometry persists to SQLite per panel.
- **Self‑healing storage.** On launch the DB is integrity‑checked; a corrupt file is quarantined and the newest healthy backup is restored. Every clean open writes a rotating snapshot via SQLite's backup API. Destructive actions snapshot first.
- **Fast lists.** `CTkScrollableFrame` rebuilds its scroll region on every child insert; a custom `ScrollList` (plain canvas + finalize‑once) plus tk‑based rows keeps filtering thousands of records feeling instant.
- **A tiny Markdown renderer.** `md_widget.py` is a dependency‑free Markdown‑to‑Tk renderer so stat blocks and rules read like documents, not raw text.
- **Header‑driven CSV detection.** Imports figure out which table a CSV belongs to from its columns first, falling back to the filename — so dropping in a folder of mixed exports "just works."

---

## 🗺️ Roadmap

- [ ] In‑app screenshots & a short demo GIF
- [ ] **Arcane Sword** — companion player‑facing character builder (reuses this app's schema & compendium)
- [ ] Theming options beyond the default dark palette
- [ ] Packaged executable (PyInstaller) for one‑download installs

---

## 📜 License

Released under the **MIT License** — see [`LICENSE`](LICENSE). Free to use, modify, and share.

---

<div align="center">

*Built for DMs who'd rather be running the game than alt‑tabbing through ten browser tabs.*

</div>
