"""Database layer — all SQLite access for Arcane Shield."""
import sqlite3
import json
import os
import re
import csv
import io
from pathlib import Path


# ── Bestiary source classification ──────────────────────────────────────────────
# Statblocks carry a "*Source: <book>*" line. Official D&D (WotC) books are kept by
# name; anything else (third-party / unknown) is bucketed as "Homebrew" per request.
_SRC_RE = re.compile(r"\*Source:\s*(.+?)\s*\*")
_OFFICIAL_SOURCES = (
    "monster manual", "volo's guide to monsters", "mordenkainen's tome of foes",
    "essentials kit", "5e core rules", "player's handbook",
    "dungeon master's guide", "tasha's cauldron of everything",
    "xanathar's guide to everything", "fizban's treasury of dragons",
    "adventures", "extra (adventurers league)",
)


def classify_bestiary_source(statblock_md: str) -> str:
    """Return the official source-book name, or 'Homebrew' if not official."""
    m = _SRC_RE.search(statblock_md or "")
    if not m:
        return "Homebrew"
    raw = m.group(1).strip()
    base = re.sub(r"\s*\((?:SRD|BR)\)\s*$", "", raw).strip()  # drop (SRD)/(BR) qualifier
    low = base.lower()
    for off in _OFFICIAL_SOURCES:
        if low == off or low.startswith(off):
            if low.startswith("monster manual"):
                return "Monster Manual"
            return base
    return "Homebrew"


def _db_path() -> Path:
    data_dir = Path(os.environ.get("APPDATA", Path.home())) / "ArcaneShield"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "arcane-shield.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            character_name TEXT NOT NULL,
            ac INTEGER NOT NULL DEFAULT 10,
            max_hp INTEGER NOT NULL DEFAULT 1,
            initiative_mod INTEGER NOT NULL DEFAULT 0,
            passive_perception INTEGER NOT NULL DEFAULT 10,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS magic_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            item_type TEXT NOT NULL DEFAULT '',
            rarity TEXT NOT NULL DEFAULT 'Common',
            requires_attunement INTEGER NOT NULL DEFAULT 0,
            attunement_requirement TEXT,
            description TEXT NOT NULL DEFAULT '',
            mechanical_effect TEXT NOT NULL DEFAULT '',
            charges INTEGER,
            source_campaign TEXT,
            tags TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS bestiary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ac INTEGER NOT NULL DEFAULT 10,
            max_hp INTEGER NOT NULL DEFAULT 1,
            initiative_mod INTEGER NOT NULL DEFAULT 0,
            cr TEXT NOT NULL DEFAULT '0',
            statblock_md TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '[]',
            source TEXT NOT NULL DEFAULT 'Homebrew'
        );
        CREATE TABLE IF NOT EXISTS mechanics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body_md TEXT NOT NULL DEFAULT '',
            campaign TEXT,
            tags TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body_md TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_label TEXT NOT NULL,
            note_date TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT NOT NULL,
            item_name TEXT NOT NULL,
            price TEXT NOT NULL DEFAULT '',
            quantity INTEGER NOT NULL DEFAULT 1,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS party_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            owner TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS saved_encounters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            state_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS dm_shield_tabs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS dm_shield_panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tab_id INTEGER NOT NULL REFERENCES dm_shield_tabs(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            width INTEGER NOT NULL DEFAULT 1,
            panel_type TEXT NOT NULL DEFAULT 'text',
            panel_height INTEGER NOT NULL DEFAULT 260,
            pos_x INTEGER NOT NULL DEFAULT 20,
            pos_y INTEGER NOT NULL DEFAULT 20,
            width_px INTEGER NOT NULL DEFAULT 360,
            height_px INTEGER NOT NULL DEFAULT 260
        );
    """)
    # Backfill columns for DBs that predate them
    for col, defn in [
        ("panel_type",   "TEXT NOT NULL DEFAULT 'text'"),
        ("panel_height", "INTEGER NOT NULL DEFAULT 260"),
        ("pos_x",        "INTEGER NOT NULL DEFAULT 20"),
        ("pos_y",        "INTEGER NOT NULL DEFAULT 20"),
        ("width_px",     "INTEGER NOT NULL DEFAULT 360"),
        ("height_px",    "INTEGER NOT NULL DEFAULT 260"),
    ]:
        try:
            conn.execute(f"ALTER TABLE dm_shield_panels ADD COLUMN {col} {defn}")
        except Exception:
            pass
    # Add bestiary.source and backfill it once (only runs when newly added)
    try:
        conn.execute("ALTER TABLE bestiary ADD COLUMN source TEXT NOT NULL DEFAULT 'Homebrew'")
        for r in conn.execute("SELECT id, statblock_md FROM bestiary").fetchall():
            conn.execute("UPDATE bestiary SET source=? WHERE id=?",
                         (classify_bestiary_source(r[1]), r[0]))
    except Exception:
        pass
    conn.commit()


def _rows(rs) -> list[dict]:
    return [dict(r) for r in rs]


def _tags_in(row: dict) -> dict:
    if "tags" in row:
        row["tags"] = json.loads(row["tags"] or "[]")
    return row


def _tag_list(tags) -> list[str]:
    if isinstance(tags, list):
        return tags
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(";") if t.strip()]
    return []


class Database:
    def __init__(self):
        self.conn = _connect()
        _migrate(self.conn)
        self._bulk = False  # when True, create_* defer committing (see import_csv)

    def _autocommit(self):
        """Commit unless a bulk operation is batching writes into one transaction."""
        if not self._bulk:
            self.conn.commit()

    # ── Players ────────────────────────────────────────────────────────────────

    def list_players(self) -> list[dict]:
        return _rows(self.conn.execute(
            "SELECT * FROM players ORDER BY character_name"
        ).fetchall())

    def create_player(self, d: dict) -> int:
        cur = self.conn.execute(
            "INSERT INTO players (player_name, character_name, ac, max_hp, initiative_mod, passive_perception, notes) "
            "VALUES (?,?,?,?,?,?,?)",
            (d["player_name"], d["character_name"], int(d.get("ac", 10)),
             int(d.get("max_hp", 1)), int(d.get("initiative_mod", 0)),
             int(d.get("passive_perception", 10)), d.get("notes") or None)
        )
        self._autocommit()
        return cur.lastrowid

    def update_player(self, id: int, d: dict) -> None:
        self.conn.execute(
            "UPDATE players SET player_name=?, character_name=?, ac=?, max_hp=?, "
            "initiative_mod=?, passive_perception=?, notes=? WHERE id=?",
            (d["player_name"], d["character_name"], int(d.get("ac", 10)),
             int(d.get("max_hp", 1)), int(d.get("initiative_mod", 0)),
             int(d.get("passive_perception", 10)), d.get("notes") or None, id)
        )
        self.conn.commit()

    def delete_player(self, id: int) -> None:
        self.conn.execute("DELETE FROM players WHERE id=?", (id,))
        self.conn.commit()

    # ── Magic Items ────────────────────────────────────────────────────────────

    def list_items(self, search="", item_type="", rarity="",
                   attunement="", tag="") -> list[dict]:
        q = "SELECT * FROM magic_items WHERE 1=1"
        p: list = []
        if search:
            q += " AND (name LIKE ? OR description LIKE ?)"; p += [f"%{search}%", f"%{search}%"]
        if item_type:
            q += " AND item_type=?"; p.append(item_type)
        if rarity:
            q += " AND rarity=?"; p.append(rarity)
        if attunement == "yes":
            q += " AND requires_attunement=1"
        elif attunement == "no":
            q += " AND requires_attunement=0"
        q += " ORDER BY name"
        rows = [_tags_in(r) for r in _rows(self.conn.execute(q, p).fetchall())]
        if tag:
            rows = [r for r in rows if tag in r.get("tags", [])]
        return rows

    def create_item(self, d: dict) -> int:
        tags = json.dumps(_tag_list(d.get("tags", [])))
        cur = self.conn.execute(
            "INSERT INTO magic_items (name,item_type,rarity,requires_attunement,attunement_requirement,"
            "description,mechanical_effect,charges,source_campaign,tags) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (d["name"], d.get("item_type",""), d.get("rarity","Common"),
             1 if d.get("requires_attunement") else 0, d.get("attunement_requirement") or None,
             d.get("description",""), d.get("mechanical_effect",""),
             d.get("charges") or None, d.get("source_campaign") or None, tags)
        )
        self._autocommit()
        return cur.lastrowid

    def update_item(self, id: int, d: dict) -> None:
        tags = json.dumps(_tag_list(d.get("tags", [])))
        self.conn.execute(
            "UPDATE magic_items SET name=?,item_type=?,rarity=?,requires_attunement=?,"
            "attunement_requirement=?,description=?,mechanical_effect=?,charges=?,source_campaign=?,tags=? WHERE id=?",
            (d["name"], d.get("item_type",""), d.get("rarity","Common"),
             1 if d.get("requires_attunement") else 0, d.get("attunement_requirement") or None,
             d.get("description",""), d.get("mechanical_effect",""),
             d.get("charges") or None, d.get("source_campaign") or None, tags, id)
        )
        self.conn.commit()

    def delete_item(self, id: int) -> None:
        self.conn.execute("DELETE FROM magic_items WHERE id=?", (id,)); self.conn.commit()

    def item_types(self) -> list[str]:
        return [r[0] for r in self.conn.execute(
            "SELECT DISTINCT item_type FROM magic_items WHERE item_type!='' ORDER BY item_type"
        ).fetchall()]

    def _distinct_tags(self, table: str) -> list[str]:
        """Collect the unique set of tags across every row of a tagged table."""
        out: set[str] = set()
        for r in self.conn.execute(f"SELECT tags FROM {table}").fetchall():
            try:
                for t in json.loads(r[0] or "[]"):
                    if t:
                        out.add(t)
            except Exception:
                pass
        return sorted(out, key=str.lower)

    def item_tags(self) -> list[str]:
        return self._distinct_tags("magic_items")

    # ── Bestiary ───────────────────────────────────────────────────────────────

    def list_bestiary(self, search="", cr="", tag="", source="") -> list[dict]:
        q = "SELECT * FROM bestiary WHERE 1=1"; p: list = []
        if search:
            q += " AND name LIKE ?"; p.append(f"%{search}%")
        if cr:
            q += " AND cr=?"; p.append(cr)
        if source:
            q += " AND source=?"; p.append(source)
        q += " ORDER BY name"
        rows = [_tags_in(r) for r in _rows(self.conn.execute(q, p).fetchall())]
        if tag:
            rows = [r for r in rows if tag in r.get("tags", [])]
        return rows

    def create_bestiary_entry(self, d: dict) -> int:
        tags = json.dumps(_tag_list(d.get("tags", [])))
        source = d.get("source") or classify_bestiary_source(d.get("statblock_md", ""))
        cur = self.conn.execute(
            "INSERT INTO bestiary (name,ac,max_hp,initiative_mod,cr,statblock_md,tags,source) VALUES (?,?,?,?,?,?,?,?)",
            (d["name"], int(d.get("ac",10)), int(d.get("max_hp",1)),
             int(d.get("initiative_mod",0)), d.get("cr","0"), d.get("statblock_md",""), tags, source)
        )
        self._autocommit()
        return cur.lastrowid

    def update_bestiary_entry(self, id: int, d: dict) -> None:
        tags = json.dumps(_tag_list(d.get("tags", [])))
        source = d.get("source") or classify_bestiary_source(d.get("statblock_md", ""))
        self.conn.execute(
            "UPDATE bestiary SET name=?,ac=?,max_hp=?,initiative_mod=?,cr=?,statblock_md=?,tags=?,source=? WHERE id=?",
            (d["name"], int(d.get("ac",10)), int(d.get("max_hp",1)),
             int(d.get("initiative_mod",0)), d.get("cr","0"), d.get("statblock_md",""), tags, source, id)
        )
        self.conn.commit()

    def delete_bestiary_entry(self, id: int) -> None:
        self.conn.execute("DELETE FROM bestiary WHERE id=?", (id,)); self.conn.commit()

    def bestiary_crs(self) -> list[str]:
        return [r[0] for r in self.conn.execute(
            "SELECT DISTINCT cr FROM bestiary ORDER BY CAST(cr AS REAL)"
        ).fetchall()]

    def bestiary_types(self) -> list[str]:
        """Monster types/keywords drawn from tags (e.g. Undead, Dragon, Fiend)."""
        return self._distinct_tags("bestiary")

    def bestiary_sources(self) -> list[str]:
        """Distinct source books — official names sorted first, Homebrew last."""
        srcs = [r[0] for r in self.conn.execute(
            "SELECT DISTINCT source FROM bestiary WHERE source!='' ORDER BY source"
        ).fetchall()]
        # Keep 'Homebrew' at the bottom of the list.
        srcs = [s for s in srcs if s != "Homebrew"] + (["Homebrew"] if "Homebrew" in srcs else [])
        return srcs

    # ── Mechanics ──────────────────────────────────────────────────────────────

    def list_mechanics(self, search="", campaign="", tag="") -> list[dict]:
        q = "SELECT * FROM mechanics WHERE 1=1"; p: list = []
        if search:
            q += " AND (title LIKE ? OR body_md LIKE ?)"; p += [f"%{search}%", f"%{search}%"]
        if campaign:
            q += " AND campaign=?"; p.append(campaign)
        q += " ORDER BY title"
        rows = [_tags_in(r) for r in _rows(self.conn.execute(q, p).fetchall())]
        if tag:
            rows = [r for r in rows if tag in r.get("tags", [])]
        return rows

    def mechanic_campaigns(self) -> list[str]:
        return [r[0] for r in self.conn.execute(
            "SELECT DISTINCT campaign FROM mechanics WHERE campaign IS NOT NULL AND campaign!='' ORDER BY campaign"
        ).fetchall()]

    def mechanic_tags(self) -> list[str]:
        """Mechanic categories drawn from tags (e.g. Combat, Resting, Travel)."""
        return self._distinct_tags("mechanics")

    def create_mechanic(self, d: dict) -> int:
        tags = json.dumps(_tag_list(d.get("tags", [])))
        cur = self.conn.execute(
            "INSERT INTO mechanics (title,body_md,campaign,tags) VALUES (?,?,?,?)",
            (d["title"], d.get("body_md",""), d.get("campaign") or None, tags)
        )
        self._autocommit()
        return cur.lastrowid

    def update_mechanic(self, id: int, d: dict) -> None:
        tags = json.dumps(_tag_list(d.get("tags", [])))
        self.conn.execute(
            "UPDATE mechanics SET title=?,body_md=?,campaign=?,tags=? WHERE id=?",
            (d["title"], d.get("body_md",""), d.get("campaign") or None, tags, id)
        )
        self.conn.commit()

    def delete_mechanic(self, id: int) -> None:
        self.conn.execute("DELETE FROM mechanics WHERE id=?", (id,)); self.conn.commit()

    # ── Campaigns ──────────────────────────────────────────────────────────────

    def list_campaigns(self, search="", tag="") -> list[dict]:
        q = "SELECT * FROM campaigns WHERE 1=1"; p: list = []
        if search:
            q += " AND (title LIKE ? OR body_md LIKE ?)"; p += [f"%{search}%", f"%{search}%"]
        q += " ORDER BY title"
        rows = [_tags_in(r) for r in _rows(self.conn.execute(q, p).fetchall())]
        if tag:
            rows = [r for r in rows if tag in r.get("tags", [])]
        return rows

    def campaign_tags(self) -> list[str]:
        return self._distinct_tags("campaigns")

    def create_campaign(self, d: dict) -> int:
        tags = json.dumps(_tag_list(d.get("tags", [])))
        cur = self.conn.execute(
            "INSERT INTO campaigns (title,body_md,tags) VALUES (?,?,?)",
            (d["title"], d.get("body_md",""), tags)
        )
        self._autocommit()
        return cur.lastrowid

    def update_campaign(self, id: int, d: dict) -> None:
        tags = json.dumps(_tag_list(d.get("tags", [])))
        self.conn.execute(
            "UPDATE campaigns SET title=?,body_md=?,tags=? WHERE id=?",
            (d["title"], d.get("body_md",""), tags, id)
        )
        self.conn.commit()

    def delete_campaign(self, id: int) -> None:
        self.conn.execute("DELETE FROM campaigns WHERE id=?", (id,)); self.conn.commit()

    # ── Notes ──────────────────────────────────────────────────────────────────

    def list_notes(self, session_label="", date_prefix="") -> list[dict]:
        q = "SELECT * FROM notes WHERE 1=1"; p: list = []
        if session_label:
            q += " AND session_label=?"; p.append(session_label)
        if date_prefix:
            q += " AND note_date LIKE ?"; p.append(f"{date_prefix}%")
        q += " ORDER BY session_label DESC, note_date DESC, id DESC"
        return _rows(self.conn.execute(q, p).fetchall())

    def note_sessions(self) -> list[str]:
        return [r[0] for r in self.conn.execute(
            "SELECT DISTINCT session_label FROM notes ORDER BY session_label"
        ).fetchall()]

    def create_note(self, d: dict) -> int:
        cur = self.conn.execute(
            "INSERT INTO notes (session_label,note_date,body) VALUES (?,?,?)",
            (d["session_label"], d["note_date"], d["body"])
        )
        self._autocommit()
        return cur.lastrowid

    def update_note(self, id: int, d: dict) -> None:
        self.conn.execute(
            "UPDATE notes SET session_label=?,note_date=?,body=? WHERE id=?",
            (d["session_label"], d["note_date"], d["body"], id)
        )
        self.conn.commit()

    def delete_note(self, id: int) -> None:
        self.conn.execute("DELETE FROM notes WHERE id=?", (id,)); self.conn.commit()

    # ── Shops ──────────────────────────────────────────────────────────────────

    def list_shop_items(self, shop="", search="") -> list[dict]:
        q = "SELECT * FROM shops WHERE 1=1"; p: list = []
        if shop:
            q += " AND shop_name=?"; p.append(shop)
        if search:
            q += " AND item_name LIKE ?"; p.append(f"%{search}%")
        q += " ORDER BY shop_name, item_name"
        return _rows(self.conn.execute(q, p).fetchall())

    def shop_names(self) -> list[str]:
        return [r[0] for r in self.conn.execute(
            "SELECT DISTINCT shop_name FROM shops ORDER BY shop_name"
        ).fetchall()]

    def create_shop_item(self, d: dict) -> int:
        cur = self.conn.execute(
            "INSERT INTO shops (shop_name,item_name,price,quantity,notes) VALUES (?,?,?,?,?)",
            (d["shop_name"], d["item_name"], d.get("price",""), int(d.get("quantity",1)), d.get("notes") or None)
        )
        self._autocommit()
        return cur.lastrowid

    def update_shop_item(self, id: int, d: dict) -> None:
        self.conn.execute(
            "UPDATE shops SET shop_name=?,item_name=?,price=?,quantity=?,notes=? WHERE id=?",
            (d["shop_name"], d["item_name"], d.get("price",""), int(d.get("quantity",1)), d.get("notes") or None, id)
        )
        self.conn.commit()

    def delete_shop_item(self, id: int) -> None:
        self.conn.execute("DELETE FROM shops WHERE id=?", (id,)); self.conn.commit()

    # ── Party Items ────────────────────────────────────────────────────────────

    def list_party_items(self, owner="", search="") -> list[dict]:
        q = "SELECT * FROM party_items WHERE 1=1"; p: list = []
        if owner:
            q += " AND owner=?"; p.append(owner)
        if search:
            q += " AND item_name LIKE ?"; p.append(f"%{search}%")
        q += " ORDER BY owner, item_name"
        return _rows(self.conn.execute(q, p).fetchall())

    def party_owners(self) -> list[str]:
        return [r[0] for r in self.conn.execute(
            "SELECT DISTINCT owner FROM party_items ORDER BY owner"
        ).fetchall()]

    def create_party_item(self, d: dict) -> int:
        cur = self.conn.execute(
            "INSERT INTO party_items (item_name,owner,quantity,notes) VALUES (?,?,?,?)",
            (d["item_name"], d["owner"], int(d.get("quantity",1)), d.get("notes") or None)
        )
        self._autocommit()
        return cur.lastrowid

    def update_party_item(self, id: int, d: dict) -> None:
        self.conn.execute(
            "UPDATE party_items SET item_name=?,owner=?,quantity=?,notes=? WHERE id=?",
            (d["item_name"], d["owner"], int(d.get("quantity",1)), d.get("notes") or None, id)
        )
        self.conn.commit()

    def delete_party_item(self, id: int) -> None:
        self.conn.execute("DELETE FROM party_items WHERE id=?", (id,)); self.conn.commit()

    # ── Saved Encounters ───────────────────────────────────────────────────────

    def list_saved_encounters(self) -> list[dict]:
        return _rows(self.conn.execute(
            "SELECT * FROM saved_encounters ORDER BY updated_at DESC"
        ).fetchall())

    def save_encounter(self, name: str, state_json: str) -> None:
        self.conn.execute(
            "INSERT INTO saved_encounters (name,state_json,updated_at) VALUES (?,?,datetime('now')) "
            "ON CONFLICT(name) DO UPDATE SET state_json=excluded.state_json, updated_at=excluded.updated_at",
            (name, state_json)
        )
        self.conn.commit()

    def delete_saved_encounter(self, id: int) -> None:
        self.conn.execute("DELETE FROM saved_encounters WHERE id=?", (id,)); self.conn.commit()

    # ── DM Shield Tabs ─────────────────────────────────────────────────────────

    def list_dm_tabs(self) -> list[dict]:
        return _rows(self.conn.execute(
            "SELECT * FROM dm_shield_tabs ORDER BY sort_order, id"
        ).fetchall())

    def create_dm_tab(self, name: str) -> int:
        max_order = self.conn.execute(
            "SELECT COALESCE(MAX(sort_order),0) FROM dm_shield_tabs"
        ).fetchone()[0]
        cur = self.conn.execute(
            "INSERT INTO dm_shield_tabs (name, sort_order) VALUES (?,?)",
            (name, max_order + 1)
        )
        self._autocommit()
        return cur.lastrowid

    def rename_dm_tab(self, id: int, name: str) -> None:
        self.conn.execute("UPDATE dm_shield_tabs SET name=? WHERE id=?", (name, id))
        self.conn.commit()

    def delete_dm_tab(self, id: int) -> None:
        self.conn.execute("DELETE FROM dm_shield_tabs WHERE id=?", (id,))
        self.conn.commit()

    def reorder_dm_tabs(self, ordered_ids: list[int]) -> None:
        for i, tab_id in enumerate(ordered_ids):
            self.conn.execute(
                "UPDATE dm_shield_tabs SET sort_order=? WHERE id=?", (i, tab_id)
            )
        self.conn.commit()

    # ── DM Shield Panels ───────────────────────────────────────────────────────

    def list_dm_panels(self, tab_id: int) -> list[dict]:
        return _rows(self.conn.execute(
            "SELECT * FROM dm_shield_panels WHERE tab_id=? ORDER BY sort_order, id",
            (tab_id,)
        ).fetchall())

    def create_dm_panel(self, tab_id: int, title: str, content: str = "",
                        width: int = 1, panel_type: str = "text",
                        panel_height: int = 260,
                        pos_x: int = 20, pos_y: int = 20,
                        width_px: int = 360, height_px: int = 260) -> int:
        max_order = self.conn.execute(
            "SELECT COALESCE(MAX(sort_order),0) FROM dm_shield_panels WHERE tab_id=?",
            (tab_id,)
        ).fetchone()[0]
        cur = self.conn.execute(
            "INSERT INTO dm_shield_panels "
            "(tab_id,title,content,sort_order,width,panel_type,panel_height,"
            " pos_x,pos_y,width_px,height_px) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (tab_id, title, content, max_order + 1, width, panel_type, panel_height,
             pos_x, pos_y, width_px, height_px)
        )
        self._autocommit()
        return cur.lastrowid

    def update_dm_panel(self, id: int, title: str, content: str, width: int,
                        panel_type: str = "text", panel_height: int = 260) -> None:
        self.conn.execute(
            "UPDATE dm_shield_panels SET title=?, content=?, width=?, panel_type=?, panel_height=? WHERE id=?",
            (title, content, width, panel_type, panel_height, id)
        )
        self.conn.commit()

    def update_dm_panel_height(self, id: int, height: int) -> None:
        self.conn.execute(
            "UPDATE dm_shield_panels SET panel_height=? WHERE id=?", (height, id)
        )
        self.conn.commit()

    def update_dm_panel_geometry(self, id: int, pos_x: int, pos_y: int,
                                 width_px: int, height_px: int) -> None:
        """Persist a panel's free-form canvas geometry (position + size)."""
        self.conn.execute(
            "UPDATE dm_shield_panels SET pos_x=?, pos_y=?, width_px=?, height_px=? WHERE id=?",
            (pos_x, pos_y, width_px, height_px, id)
        )
        self.conn.commit()

    def update_dm_panel_content(self, id: int, content: str) -> None:
        """Lightweight update for auto-saving panel state (e.g. initiative JSON)."""
        self.conn.execute(
            "UPDATE dm_shield_panels SET content=? WHERE id=?", (content, id)
        )
        self.conn.commit()

    def delete_dm_panel(self, id: int) -> None:
        self.conn.execute("DELETE FROM dm_shield_panels WHERE id=?", (id,))
        self.conn.commit()

    def reorder_dm_panels(self, ordered_ids: list[int]) -> None:
        for i, panel_id in enumerate(ordered_ids):
            self.conn.execute(
                "UPDATE dm_shield_panels SET sort_order=? WHERE id=?", (i, panel_id)
            )
        self.conn.commit()

    # ── Bulk clear ─────────────────────────────────────────────────────────────

    CLEARABLE_TABLES = {
        "magic_items":  "Magic Items",
        "bestiary":     "Bestiary",
        "mechanics":    "Mechanics",
        "campaigns":    "Campaign Info",
        "notes":        "Notes",
        "shops":        "Shops",
        "party_items":  "Party Loot",
        "players":      "Party Roster",
    }

    def clear_table(self, table: str) -> int:
        """Delete all rows from a clearable table. Returns number of rows deleted."""
        if table not in self.CLEARABLE_TABLES:
            raise ValueError(f"Table '{table}' is not clearable.")
        cur = self.conn.execute(f"DELETE FROM {table}")
        self.conn.commit()
        return cur.rowcount

    # ── CSV Export ─────────────────────────────────────────────────────────────

    def export_csv(self, table: str) -> str:
        out = io.StringIO()
        w = csv.writer(out)

        if table == "players":
            w.writerow(["player_name","character_name","ac","max_hp","initiative_mod","passive_perception","notes"])
            for r in self.conn.execute("SELECT player_name,character_name,ac,max_hp,initiative_mod,passive_perception,notes FROM players").fetchall():
                w.writerow(list(r))

        elif table == "magic_items":
            w.writerow(["name","item_type","rarity","requires_attunement","attunement_requirement","description","mechanical_effect","charges","source_campaign","tags"])
            for r in self.conn.execute("SELECT name,item_type,rarity,requires_attunement,attunement_requirement,description,mechanical_effect,charges,source_campaign,tags FROM magic_items").fetchall():
                row = list(r)
                row[-1] = ";".join(json.loads(row[-1] or "[]"))
                w.writerow(row)

        elif table == "bestiary":
            w.writerow(["name","ac","max_hp","initiative_mod","cr","statblock_md","tags","source"])
            for r in self.conn.execute("SELECT name,ac,max_hp,initiative_mod,cr,statblock_md,tags,source FROM bestiary").fetchall():
                row = list(r)
                row[-1] = ";".join(json.loads(row[-1] or "[]"))
                w.writerow(row)

        elif table == "mechanics":
            w.writerow(["title","body_md","campaign","tags"])
            for r in self.conn.execute("SELECT title,body_md,campaign,tags FROM mechanics").fetchall():
                row = list(r)
                row[-1] = ";".join(json.loads(row[-1] or "[]"))
                w.writerow(row)

        elif table == "campaigns":
            w.writerow(["title","body_md","tags"])
            for r in self.conn.execute("SELECT title,body_md,tags FROM campaigns").fetchall():
                row = list(r)
                row[-1] = ";".join(json.loads(row[-1] or "[]"))
                w.writerow(row)

        elif table == "notes":
            w.writerow(["session_label","note_date","body"])
            for r in self.conn.execute("SELECT session_label,note_date,body FROM notes").fetchall():
                w.writerow(list(r))

        elif table == "shops":
            w.writerow(["shop_name","item_name","price","quantity","notes"])
            for r in self.conn.execute("SELECT shop_name,item_name,price,quantity,notes FROM shops").fetchall():
                w.writerow(list(r))

        elif table == "party_items":
            w.writerow(["item_name","owner","quantity","notes"])
            for r in self.conn.execute("SELECT item_name,owner,quantity,notes FROM party_items").fetchall():
                w.writerow(list(r))

        return out.getvalue()

    # ── CSV Import ─────────────────────────────────────────────────────────────

    def import_csv(self, filename: str, text: str) -> dict:
        """Auto-detect table from headers/filename and import rows."""
        try:
            reader = csv.DictReader(io.StringIO(text))
            headers = set(reader.fieldnames or [])
        except Exception as e:
            return {"table": "unknown", "inserted": 0, "skipped": 0, "errors": [str(e)]}

        table = _detect_table(headers, filename)
        if not table:
            return {"table": "unknown", "inserted": 0, "skipped": 0,
                    "errors": [f"Cannot detect table from headers: {headers}"]}

        inserted = 0; skipped = 0; errors: list[str] = []
        reader = csv.DictReader(io.StringIO(text))
        self._bulk = True  # batch the whole file into ONE transaction (avoids per-row fsync)
        for i, row in enumerate(reader, start=2):
            try:
                row = {k: (v.strip() if v else v) for k, v in row.items()}
                if table == "players":
                    if not row.get("player_name") or not row.get("character_name"):
                        skipped += 1; continue
                    self.create_player({
                        "player_name": row["player_name"],
                        "character_name": row["character_name"],
                        "ac": _int(row.get("ac"), 10),
                        "max_hp": _int(row.get("max_hp"), 1),
                        "initiative_mod": _int(row.get("initiative_mod"), 0),
                        "passive_perception": _int(row.get("passive_perception"), 10),
                        "notes": row.get("notes"),
                    })
                elif table == "magic_items":
                    if not row.get("name"): skipped += 1; continue
                    self.create_item({
                        "name": row["name"],
                        "item_type": row.get("item_type",""),
                        "rarity": row.get("rarity","Common"),
                        "requires_attunement": row.get("requires_attunement","").lower() in ("1","true","yes"),
                        "attunement_requirement": row.get("attunement_requirement"),
                        "description": row.get("description",""),
                        "mechanical_effect": row.get("mechanical_effect",""),
                        "charges": _int(row.get("charges"), None),
                        "source_campaign": row.get("source_campaign"),
                        "tags": _tag_list(row.get("tags","")),
                    })
                elif table == "bestiary":
                    if not row.get("name"): skipped += 1; continue
                    self.create_bestiary_entry({
                        "name": row["name"],
                        "ac": _int(row.get("ac"), 10),
                        "max_hp": _int(row.get("max_hp"), 1),
                        "initiative_mod": _int(row.get("initiative_mod"), 0),
                        "cr": row.get("cr","0"),
                        "statblock_md": row.get("statblock_md",""),
                        "tags": _tag_list(row.get("tags","")),
                        "source": row.get("source"),  # else auto-classified from statblock
                    })
                elif table == "mechanics":
                    if not row.get("title"): skipped += 1; continue
                    self.create_mechanic({
                        "title": row["title"],
                        "body_md": row.get("body_md",""),
                        "campaign": row.get("campaign"),
                        "tags": _tag_list(row.get("tags","")),
                    })
                elif table == "campaigns":
                    if not row.get("title"): skipped += 1; continue
                    self.create_campaign({
                        "title": row["title"],
                        "body_md": row.get("body_md",""),
                        "tags": _tag_list(row.get("tags","")),
                    })
                elif table == "notes":
                    if not row.get("session_label"): skipped += 1; continue
                    self.create_note({
                        "session_label": row["session_label"],
                        "note_date": row.get("note_date",""),
                        "body": row.get("body",""),
                    })
                elif table == "shops":
                    if not row.get("shop_name") or not row.get("item_name"): skipped += 1; continue
                    self.create_shop_item({
                        "shop_name": row["shop_name"],
                        "item_name": row["item_name"],
                        "price": row.get("price",""),
                        "quantity": _int(row.get("quantity"), 1),
                        "notes": row.get("notes"),
                    })
                elif table == "party_items":
                    if not row.get("item_name"): skipped += 1; continue
                    self.create_party_item({
                        "item_name": row["item_name"],
                        "owner": row.get("owner",""),
                        "quantity": _int(row.get("quantity"), 1),
                        "notes": row.get("notes"),
                    })
                inserted += 1
            except Exception as e:
                errors.append(f"Row {i}: {e}")
        try:
            self.conn.commit()  # single commit for the whole file
        finally:
            self._bulk = False
        return {"table": table, "inserted": inserted, "skipped": skipped, "errors": errors}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _int(v, default):
    try:
        return int(v) if v not in (None, "", "None") else default
    except (ValueError, TypeError):
        return default


def _detect_table(headers: set, filename: str) -> str | None:
    h = {c.lower() for c in headers}

    # Header-based detection (most reliable)
    if "player_name" in h and "character_name" in h:
        return "players"
    if "shop_name" in h and "item_name" in h:
        return "shops"
    if "item_name" in h and "owner" in h:
        return "party_items"
    if "session_label" in h and "note_date" in h:
        return "notes"
    if "item_type" in h and "rarity" in h:
        return "magic_items"
    if any("statblock" in c for c in h) or ("initiative_mod" in h and "cr" in h):
        return "bestiary"
    if "body_md" in h and "campaign" in h:
        return "mechanics"
    if "body_md" in h:
        return "campaigns"

    # Filename fallback
    fn = filename.lower()
    if any(x in fn for x in ("player", "roster")):
        return "players"
    if any(x in fn for x in ("party_item", "loot", "inventory")):
        return "party_items"
    if any(x in fn for x in ("magic", "item")):
        return "magic_items"
    if any(x in fn for x in ("bestiar", "monster", "creature")):
        return "bestiary"
    if any(x in fn for x in ("mechanic", "rule")):
        return "mechanics"
    if any(x in fn for x in ("campaign", "world")):
        return "campaigns"
    if any(x in fn for x in ("note", "session")):
        return "notes"
    if any(x in fn for x in ("shop", "vendor", "store")):
        return "shops"

    return None
