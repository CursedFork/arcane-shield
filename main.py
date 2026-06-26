"""Arcane Shield — Python desktop app entry point."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import ctypes
import customtkinter as ctk
from db import Database

# Tell Windows this is its own app so the taskbar shows the custom icon
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("arcane.shield.dm")
except Exception:
    pass
from pages.items import ItemsPage
from pages.bestiary import BestiaryPage
from pages.spells import SpellsPage
from pages.conditions import ConditionsPage
from pages.mechanics import MechanicsPage
from pages.campaigns import CampaignsPage
from pages.notes import NotesPage
from pages.shops import ShopsPage
from pages.initiative import InitiativePage
from pages.bulk_import import BulkImportPage
from pages.dm_shield import DmShieldPage

# ── Colour palette ─────────────────────────────────────────────────────────────
BG       = "#0f0f13"
SURFACE  = "#1a1a24"
SURFACE2 = "#22222f"
BORDER   = "#2e2e3e"
ACCENT   = "#7c5cbf"
TEXT     = "#e2e0f0"
MUTED    = "#8a8aa0"

# DM Shield is pinned to the top, Bulk Import to the bottom; content tabs sit
# between them. (New content tabs get added to NAV_CONTENT.)
NAV_TOP = [
    ("dm_shield",  "🛡  DM Shield"),
]
NAV_CONTENT = [
    ("items",      "✦  Magic Items"),
    ("bestiary",   "☠  Bestiary"),
    ("spells",     "✨  Spells"),
    ("conditions", "🜸  Conditions"),
    ("mechanics",  "⚙  Mechanics"),
    ("campaigns",  "📖  Campaigns"),
    ("notes",      "✎  Notes"),
    ("shops",      "⚖  Shops & Loot"),
    ("initiative", "⚔  Initiative"),
]
NAV_BOTTOM = [
    ("import",     "⬆  Bulk Import"),
]
NAV_ITEMS = NAV_TOP + NAV_CONTENT + NAV_BOTTOM


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Arcane Shield")
        self.geometry("1400x900")
        self.minsize(1000, 600)
        self.configure(fg_color=BG)

        # Try to set window icon
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.db = Database()

        # Grid: sidebar col 0 (fixed) + content col 1 (flex)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content()

    # ── Sidebar ────────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=200, fg_color=SURFACE, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)

        ctk.CTkLabel(
            sb, text="⚔ ARCANE SHIELD",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT
        ).pack(pady=(24, 4), padx=16, anchor="w")

        ctk.CTkLabel(
            sb, text="DM Reference Tool",
            font=ctk.CTkFont(size=11),
            text_color=MUTED
        ).pack(pady=(0, 20), padx=16, anchor="w")

        self._nav_btns: dict[str, ctk.CTkButton] = {}
        self._nav_defaults: dict[str, dict] = {}

        def make_nav_btn(key, label, *, fg="transparent", text=MUTED,
                         border=0, border_color=BORDER, **pack_kw):
            btn = ctk.CTkButton(
                sb, text=label, anchor="w",
                fg_color=fg, hover_color=SURFACE2,
                text_color=text, font=ctk.CTkFont(size=13),
                corner_radius=0 if not border else 6, height=38,
                border_width=border, border_color=border_color,
                command=lambda k=key: self.show_page(k)
            )
            btn.pack(**pack_kw)
            self._nav_btns[key] = btn
            self._nav_defaults[key] = {"fg_color": fg, "text_color": text}
            return btn

        # ── Top: DM Shield (primary, emphasized) ─────────────────────────────
        for key, label in NAV_TOP:
            make_nav_btn(key, label, text=TEXT, fill="x", padx=0, pady=0)
        ctk.CTkFrame(sb, height=1, fg_color=BORDER).pack(fill="x", padx=12, pady=(6, 6))

        # ── Middle: content tabs ─────────────────────────────────────────────
        for key, label in NAV_CONTENT:
            make_nav_btn(key, label, fill="x", padx=0, pady=0)

        # ── Bottom: DB label, then a clearly-set-apart Bulk Import ───────────
        from db import _db_path
        db_p = str(_db_path())
        ctk.CTkLabel(
            sb, text=f"DB: {os.path.basename(db_p)}",
            font=ctk.CTkFont(size=9), text_color=MUTED, wraplength=180
        ).pack(side="bottom", pady=8, padx=8)

        for key, label in NAV_BOTTOM:
            make_nav_btn(key, label, text=ACCENT, border=2, border_color=ACCENT,
                         side="bottom", fill="x", padx=10, pady=(0, 6))
        ctk.CTkFrame(sb, height=1, fg_color=BORDER).pack(side="bottom", fill="x",
                                                         padx=12, pady=(6, 4))

    # ── Content area ───────────────────────────────────────────────────────────

    def _build_content(self):
        self._content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._pages: dict[str, ctk.CTkFrame] = {
            "items":      ItemsPage(self._content, self.db),
            "bestiary":   BestiaryPage(self._content, self.db),
            "spells":     SpellsPage(self._content, self.db),
            "conditions": ConditionsPage(self._content, self.db),
            "mechanics":  MechanicsPage(self._content, self.db),
            "campaigns":  CampaignsPage(self._content, self.db),
            "notes":      NotesPage(self._content, self.db),
            "shops":      ShopsPage(self._content, self.db),
            "initiative": InitiativePage(self._content, self.db),
            "import":     BulkImportPage(self._content, self.db),
            "dm_shield":  DmShieldPage(self._content, self.db),
        }

        for page in self._pages.values():
            page.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
            page.grid_remove()

        self._current: str | None = None
        self.show_page("items")

    # ── Navigation ─────────────────────────────────────────────────────────────

    def show_page(self, name: str):
        if self._current:
            self._pages[self._current].grid_remove()
            btn = self._nav_btns.get(self._current)
            if btn:
                btn.configure(**self._nav_defaults.get(self._current,
                              {"fg_color": "transparent", "text_color": MUTED}))

        self._current = name
        self._pages[name].grid()
        self._pages[name].refresh()

        btn = self._nav_btns.get(name)
        if btn:
            btn.configure(text_color=TEXT, fg_color=SURFACE2)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = App()
    app.mainloop()
