"""DM Shield page — customizable tab/panel dashboard with live resource widgets."""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import dice as dice_module
from datetime import date
from pages.md_widget import MarkdownText

BG       = "#0f0f13"
SURFACE  = "#1a1a24"
SURFACE2 = "#22222f"
SURFACE3 = "#2a2a3a"
BORDER   = "#2e2e3e"
ACCENT   = "#7c5cbf"
ACCENT_H = "#9472d8"
TEXT     = "#e2e0f0"
MUTED    = "#8a8aa0"
DANGER   = "#c0392b"
SUCCESS  = "#27ae60"
DRAG_HL  = "#3d2f5e"
GHOST_BG = "#4a3580"

PANEL_TYPES = {
    "text":        "📝  Custom Text",
    "notes":       "✎  Quick Notes",
    "initiative":  "⚔  Initiative",
    "mechanics":   "⚙  Mechanics",
    "magic_items": "✦  Magic Items",
    "bestiary":    "☠  Bestiary",
    "campaigns":   "📖  Campaign Info",
    "shops":       "⚖  Shops",
    "party_items": "🎒  Party Loot",
}

RARITY_COLORS = {
    "Common": "#aaaaaa", "Uncommon": "#1eff00", "Rare": "#0070dd",
    "Very Rare": "#a335ee", "Legendary": "#ff8000", "Artifact": "#e6cc80",
}

# Free-form canvas layout constants
MIN_W      = 220     # minimum panel width  (px)
MIN_H      = 120     # minimum panel height (px)
HEADER_H   = 34      # panel title-bar height
GRIP       = 16      # corner resize-grip size
EDGE       = 8       # edge resize-strip thickness
MARGIN     = 16      # gutter when auto-arranging
GAP        = 14      # gap between auto-arranged panels
DEF_W      = 360     # default new-panel width
DEF_H      = 260     # default new-panel height


class DmShieldPage(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._active_tab: dict | None = None
        self._panels: list[dict] = []

        # Canvas item registry: panel_id -> dict(item, frame, x, y, w, h)
        self._items: dict[int, dict] = {}
        # Active gesture state (move or resize)
        self._gesture: dict | None = None

        self._build()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Tab bar ──────────────────────────────────────────────────────────
        self._tab_bar = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8, height=46)
        self._tab_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 4))
        self._tab_bar.grid_propagate(False)

        self._tab_inner = ctk.CTkFrame(self._tab_bar, fg_color="transparent")
        self._tab_inner.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        ctk.CTkButton(
            self._tab_bar, text="+ Tab", width=64, height=30,
            fg_color="transparent", hover_color=SURFACE2,
            text_color=MUTED, font=ctk.CTkFont(size=12),
            command=self._new_tab
        ).pack(side="right", padx=(0, 8), pady=8)

        ctk.CTkButton(
            self._tab_bar, text="⊞ Layouts", width=86, height=30,
            fg_color="transparent", hover_color=SURFACE2,
            text_color=MUTED, font=ctk.CTkFont(size=12),
            command=self._open_layouts_menu
        ).pack(side="right", padx=(0, 2), pady=8)

        ctk.CTkButton(
            self._tab_bar, text="+ Panel", width=72, height=30,
            fg_color=ACCENT, hover_color=ACCENT_H,
            text_color=TEXT, font=ctk.CTkFont(size=12),
            command=self._new_panel
        ).pack(side="right", padx=(0, 2), pady=8)

        # ── Free-form canvas (absolute panel positioning) ────────────────────
        wrap = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        wrap.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0, bd=0)
        self._canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self._vbar = ctk.CTkScrollbar(wrap, orientation="vertical",
                                      command=self._canvas.yview,
                                      button_color=ACCENT)
        self._vbar.grid(row=0, column=1, sticky="ns", pady=2)
        self._canvas.configure(yscrollcommand=self._vbar.set)

        # Mouse-wheel scrolls the canvas (when not over an inner scroll area)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Configure>", lambda e: self._update_scrollregion())

    # ── Tab bar ────────────────────────────────────────────────────────────────

    def _render_tabs(self):
        for w in self._tab_inner.winfo_children():
            w.destroy()
        for tab in self.db.list_dm_tabs():
            is_active = self._active_tab and tab["id"] == self._active_tab["id"]
            btn = ctk.CTkButton(
                self._tab_inner, text=tab["name"], height=30,
                fg_color=ACCENT if is_active else "transparent",
                hover_color=ACCENT_H if is_active else SURFACE2,
                text_color=TEXT if is_active else MUTED,
                font=ctk.CTkFont(size=13), corner_radius=6,
                command=lambda t=tab: self._switch_tab(t)
            )
            btn.pack(side="left", padx=(0, 2))
            btn.bind("<Button-3>", lambda e, t=tab: self._tab_context(e, t))

    def _switch_tab(self, tab: dict):
        self._active_tab = tab
        self._render_tabs()
        self._load_panels()

    def _tab_context(self, event, tab: dict):
        menu = tk.Menu(self, tearoff=0, bg=SURFACE2, fg=TEXT,
                       activebackground=ACCENT, activeforeground=TEXT, bd=0)
        menu.add_command(label="Rename", command=lambda: self._rename_tab(tab))
        menu.add_separator()
        menu.add_command(label="Delete Tab", foreground=DANGER,
                         command=lambda: self._delete_tab(tab))
        menu.tk_popup(event.x_root, event.y_root)

    def _new_tab(self):
        name = simpledialog.askstring("New Tab", "Tab name:", parent=self)
        if not name:
            return
        tab_id = self.db.create_dm_tab(name.strip())
        tabs = self.db.list_dm_tabs()
        new_tab = next((t for t in tabs if t["id"] == tab_id), None)
        self._switch_tab(new_tab or tabs[-1])

    def _rename_tab(self, tab: dict):
        name = simpledialog.askstring("Rename Tab", "New name:",
                                       initialvalue=tab["name"], parent=self)
        if name and name.strip():
            self.db.rename_dm_tab(tab["id"], name.strip())
            if self._active_tab and self._active_tab["id"] == tab["id"]:
                self._active_tab["name"] = name.strip()
            self._render_tabs()

    def _delete_tab(self, tab: dict):
        if not messagebox.askyesno("Delete Tab",
                                   f"Delete '{tab['name']}' and all its panels?"):
            return
        self.db.delete_dm_tab(tab["id"])
        if self._active_tab and self._active_tab["id"] == tab["id"]:
            self._active_tab = None
            tabs = self.db.list_dm_tabs()
            if tabs:
                self._switch_tab(tabs[0])
            else:
                self._render_tabs()
                self._render_panels([])
        else:
            self._render_tabs()

    # ── Panel loading ──────────────────────────────────────────────────────────

    def _load_panels(self):
        if not self._active_tab:
            self._render_panels([])
            return
        self._panels = self.db.list_dm_panels(self._active_tab["id"])
        self._dedupe_positions(self._panels)
        self._render_panels(self._panels)

    def _dedupe_positions(self, panels: list[dict]):
        """One-time fix: panels migrated from the old grid layout all share the
        default (20,20). Cascade any exact-overlap duplicates so none hide."""
        seen: set[tuple[int, int]] = set()
        changed = False
        for i, p in enumerate(panels):
            pos = (p.get("pos_x", 20), p.get("pos_y", 20))
            if pos in seen:
                nx = MARGIN + (i * 30) % 600
                ny = MARGIN + (i * 30) % 360
                p["pos_x"], p["pos_y"] = nx, ny
                self.db.update_dm_panel_geometry(
                    p["id"], nx, ny,
                    max(MIN_W, p.get("width_px", DEF_W)),
                    max(MIN_H, p.get("height_px", DEF_H)))
                changed = True
            seen.add((p.get("pos_x", 20), p.get("pos_y", 20)))
        return changed

    def _render_panels(self, panels: list[dict]):
        # Clear canvas
        self._canvas.delete("all")
        for rec in self._items.values():
            try:
                rec["frame"].destroy()
            except Exception:
                pass
        self._items = {}

        if not self._active_tab:
            self._canvas.create_text(
                30, 40, anchor="nw", fill=MUTED, font=("Segoe UI", 13),
                text="No tabs yet — click  + Tab  to create your first DM screen."
            )
            return

        if not panels:
            self._canvas.create_text(
                30, 40, anchor="nw", fill=MUTED, font=("Segoe UI", 13),
                text="No panels yet — click  + Panel  to build your DM screen,\n"
                     "or pick a starter from  ⊞ Layouts."
            )
            return

        for panel in panels:
            self._place_panel(panel)
        self._update_scrollregion()

    def _place_panel(self, panel: dict):
        """Create a panel frame and embed it on the canvas at its stored geometry."""
        x = max(0, panel.get("pos_x", 20))
        y = max(0, panel.get("pos_y", 20))
        w = max(MIN_W, panel.get("width_px", DEF_W))
        h = max(MIN_H, panel.get("height_px", DEF_H))

        frame = self._make_panel_frame(panel)
        item = self._canvas.create_window(x, y, anchor="nw", window=frame,
                                          width=w, height=h)
        self._items[panel["id"]] = {
            "item": item, "frame": frame, "panel": panel,
            "x": x, "y": y, "w": w, "h": h,
        }

    # ── Panel shell (header + body + move/resize grips) ───────────────────────

    def _make_panel_frame(self, panel: dict) -> ctk.CTkFrame:
        ptype = panel.get("panel_type", "text")
        pid   = panel["id"]

        # The embedded window is sized by the canvas (create_window width/height),
        # so the frame itself never needs configure(height=) — fully reliable.
        outer = ctk.CTkFrame(self._canvas, fg_color=SURFACE,
                             corner_radius=8, border_color=BORDER, border_width=1)

        # ── Header (drag to MOVE) ─────────────────────────────────────────────
        header = ctk.CTkFrame(outer, fg_color=SURFACE2, corner_radius=0, height=HEADER_H)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        grip = ctk.CTkLabel(header, text="⠿", text_color=MUTED,
                            font=ctk.CTkFont(size=16), width=24, cursor="fleur")
        grip.pack(side="left", padx=(6, 2))

        type_icon = PANEL_TYPES.get(ptype, "📝  Custom Text").split("  ")[0]
        ctk.CTkLabel(header, text=f"{type_icon}  {panel['title']}", anchor="w",
                     text_color=TEXT, font=ctk.CTkFont(size=13, weight="bold")
                     ).pack(side="left", fill="x", expand=True, padx=4)

        ctk.CTkButton(header, text="✎", width=28, height=24,
                      fg_color="transparent", hover_color=SURFACE, text_color=MUTED,
                      font=ctk.CTkFont(size=12),
                      command=lambda p=panel: self._edit_panel(p)
                      ).pack(side="right")
        ctk.CTkButton(header, text="✕", width=28, height=24,
                      fg_color="transparent", hover_color=DANGER, text_color=MUTED,
                      font=ctk.CTkFont(size=11),
                      command=lambda p=panel: self._delete_panel(p)
                      ).pack(side="right")

        # ── Body ──────────────────────────────────────────────────────────────
        body = ctk.CTkFrame(outer, fg_color="transparent")
        body.pack(fill="both", expand=True, side="top")

        renderer = {
            "text":        self._body_text,
            "notes":       self._body_notes,
            "initiative":  self._body_initiative,
            "mechanics":   self._body_mechanics,
            "magic_items": self._body_magic_items,
            "bestiary":    self._body_bestiary,
            "campaigns":   self._body_campaigns,
            "shops":       self._body_shops,
            "party_items": self._body_party_items,
        }.get(ptype, self._body_text)
        renderer(body, panel)

        # ── Move bindings (header + grip) ─────────────────────────────────────
        for w in (grip, header):
            w.bind("<ButtonPress-1>",   lambda e, i=pid: self._move_start(e, i))
            w.bind("<B1-Motion>",       lambda e, i=pid: self._move_motion(e, i))
            w.bind("<ButtonRelease-1>", lambda e, i=pid: self._gesture_end(i))
            w.bind("<Button-1>",        lambda e, i=pid: self._raise_panel(i), add="+")

        # ── Resize grips (overlaid via place; kept clear of inner scrollbars) ──
        # Bottom edge → height. Reserve the right end for the corner grip so the
        # two never fight, and so neither covers the body's inner scrollbar.
        bottom = tk.Frame(outer, bg=SURFACE2, cursor="size_ns", height=EDGE)
        bottom.place(relx=0, rely=1.0, anchor="sw", x=0, y=0,
                     relwidth=1.0, width=-GRIP, height=EDGE)
        # Corner → width + height (primary resize handle)
        corner = tk.Frame(outer, bg=ACCENT, cursor="bottom_right_corner",
                          width=GRIP, height=GRIP)
        corner.place(relx=1.0, rely=1.0, anchor="se", width=GRIP, height=GRIP)

        bottom.bind("<ButtonPress-1>",  lambda e, i=pid: self._resize_start(e, i, "h"))
        bottom.bind("<B1-Motion>",      lambda e, i=pid: self._resize_motion(e, i))
        bottom.bind("<ButtonRelease-1>",lambda e, i=pid: self._gesture_end(i))
        corner.bind("<ButtonPress-1>",  lambda e, i=pid: self._resize_start(e, i, "wh"))
        corner.bind("<B1-Motion>",      lambda e, i=pid: self._resize_motion(e, i))
        corner.bind("<ButtonRelease-1>",lambda e, i=pid: self._gesture_end(i))

        return outer

    # ── Panel body renderers ───────────────────────────────────────────────────

    def _body_text(self, parent, panel: dict):
        tb = ctk.CTkTextbox(parent, fg_color=SURFACE, text_color=TEXT,
                             border_width=0, font=ctk.CTkFont(size=12),
                             wrap="word", height=160)
        tb.insert("1.0", panel.get("content", ""))
        tb.configure(state="disabled")
        tb.pack(fill="both", expand=True, padx=8, pady=(4, 8))

    def _body_notes(self, parent, panel: dict):
        """Quick-add notes + recent notes list."""
        # Quick-add
        add_f = ctk.CTkFrame(parent, fg_color=SURFACE2, corner_radius=6)
        add_f.pack(fill="x", padx=6, pady=(6, 4))
        add_f.columnconfigure(0, weight=1)

        row_f = ctk.CTkFrame(add_f, fg_color="transparent")
        row_f.pack(fill="x", padx=6, pady=(6, 2))
        row_f.columnconfigure(0, weight=1)

        sl_var = tk.StringVar()
        ctk.CTkEntry(row_f, textvariable=sl_var, placeholder_text="Session label",
                     fg_color=SURFACE, border_color=BORDER, text_color=TEXT, height=26
                     ).pack(side="left", fill="x", expand=True, padx=(0, 4))
        date_var = tk.StringVar(value=str(date.today()))
        ctk.CTkEntry(row_f, textvariable=date_var, fg_color=SURFACE,
                     border_color=BORDER, text_color=TEXT, height=26, width=90
                     ).pack(side="right")

        body_tb = ctk.CTkTextbox(add_f, height=48, fg_color=SURFACE,
                                  border_color=BORDER, text_color=TEXT,
                                  font=ctk.CTkFont(size=12), wrap="word")
        body_tb.pack(fill="x", padx=6, pady=(0, 2))

        notes_list_ref = [None]

        def add_note():
            sl = sl_var.get().strip()
            body = body_tb.get("1.0", "end").strip()
            if not sl or not body:
                return
            self.db.create_note({"session_label": sl, "note_date": date_var.get(), "body": body})
            body_tb.delete("1.0", "end")
            _refresh_notes()

        ctk.CTkButton(add_f, text="Add Note", height=26, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=11),
                      command=add_note).pack(fill="x", padx=6, pady=(0, 6))

        # Recent notes
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_button_color=ACCENT)
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        scroll.columnconfigure(0, weight=1)
        notes_list_ref[0] = scroll

        def _refresh_notes():
            for w in scroll.winfo_children():
                w.destroy()
            for n in self.db.list_notes()[:15]:
                f = ctk.CTkFrame(scroll, fg_color=SURFACE2, corner_radius=4)
                f.pack(fill="x", padx=2, pady=1)
                ctk.CTkLabel(f, text=n["session_label"], text_color=ACCENT,
                             font=ctk.CTkFont(size=10, weight="bold"), anchor="w"
                             ).pack(anchor="w", padx=6, pady=(3, 0))
                ctk.CTkLabel(f, text=n.get("body","")[:80], text_color=TEXT,
                             font=ctk.CTkFont(size=11), anchor="w", wraplength=300
                             ).pack(anchor="w", padx=6, pady=(0, 3))

        _refresh_notes()

    def _body_initiative(self, parent, panel: dict):
        """Compact initiative tracker — state saved as JSON in panel.content."""
        try:
            state = json.loads(panel.get("content") or "{}")
        except Exception:
            state = {}

        combatants: list[dict] = state.get("combatants", [])
        turn_ref = [state.get("turn", 0)]
        round_ref = [state.get("round", 1)]

        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=6, pady=(4, 2))
        top.columnconfigure(0, weight=1)

        round_lbl = ctk.CTkLabel(top, text=f"Round {round_ref[0]}",
                                  text_color=ACCENT, font=ctk.CTkFont(size=12, weight="bold"))
        round_lbl.pack(side="left")

        list_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                             height=140, scrollbar_button_color=ACCENT)
        list_frame.pack(fill="x", padx=6, pady=(0, 2))
        list_frame.columnconfigure(0, weight=1)

        def _save_state():
            s = json.dumps({"combatants": combatants,
                            "turn": turn_ref[0], "round": round_ref[0]})
            self.db.update_dm_panel_content(panel["id"], s)
            panel["content"] = s

        def _render_list():
            for w in list_frame.winfo_children():
                w.destroy()
            combatants.sort(key=lambda c: -int(c.get("initiative", 0)))
            for i, c in enumerate(combatants):
                active = (i == turn_ref[0] % max(len(combatants), 1))
                bg = "#2a2038" if active else SURFACE2
                row = ctk.CTkFrame(list_frame, fg_color=bg, corner_radius=4)
                row.pack(fill="x", padx=2, pady=1)
                row.columnconfigure(1, weight=1)
                ctk.CTkLabel(row, text="▶" if active else f"{c.get('initiative','?')}",
                             text_color=ACCENT, font=ctk.CTkFont(size=11), width=28
                             ).grid(row=0, column=0, padx=(4,0))
                ctk.CTkLabel(row, text=c["name"], anchor="w", text_color=TEXT,
                             font=ctk.CTkFont(size=12)
                             ).grid(row=0, column=1, sticky="ew", padx=4, pady=3)
                hp = c.get("current_hp", c.get("max_hp", "?"))
                mx = c.get("max_hp", "?")
                ctk.CTkLabel(row, text=f"{hp}/{mx}HP · AC{c.get('ac','?')}",
                             text_color=MUTED, font=ctk.CTkFont(size=10)
                             ).grid(row=0, column=2, padx=(0,4))
                ctk.CTkButton(row, text="✕", width=22, height=20,
                              fg_color="transparent", hover_color=DANGER,
                              text_color=MUTED, font=ctk.CTkFont(size=10),
                              command=lambda i=i: (_remove(i))
                              ).grid(row=0, column=3, padx=(0,4))

        def _remove(i):
            if 0 <= i < len(combatants):
                combatants.pop(i)
                if turn_ref[0] >= len(combatants):
                    turn_ref[0] = max(0, len(combatants)-1)
                _save_state(); _render_list()

        def next_turn():
            if not combatants: return
            turn_ref[0] += 1
            if turn_ref[0] >= len(combatants):
                turn_ref[0] = 0
                round_ref[0] += 1
                round_lbl.configure(text=f"Round {round_ref[0]}")
            _save_state(); _render_list()

        ctk.CTkButton(top, text="▶ Next", width=72, height=26,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=TEXT,
                      font=ctk.CTkFont(size=11), command=next_turn).pack(side="right")

        ctk.CTkButton(top, text="Reset", width=60, height=26,
                      fg_color=SURFACE2, hover_color=BORDER, text_color=MUTED,
                      font=ctk.CTkFont(size=11),
                      command=lambda: (combatants.clear(),
                                       turn_ref.__setitem__(0,0),
                                       round_ref.__setitem__(0,1),
                                       round_lbl.configure(text="Round 1"),
                                       _save_state(), _render_list())
                      ).pack(side="right", padx=(0,4))

        _render_list()

        # Quick-add row
        add_row = ctk.CTkFrame(parent, fg_color="transparent")
        add_row.pack(fill="x", padx=6, pady=(0, 6))
        add_row.columnconfigure(0, weight=1)

        name_var = tk.StringVar()
        ctk.CTkEntry(add_row, textvariable=name_var, placeholder_text="Name",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=26
                     ).grid(row=0, column=0, sticky="ew", padx=(0,2))

        for col, (placeholder, attr, default) in enumerate([
            ("Init","_init_var",""), ("AC","_ac_var","10"), ("HP","_hp_var","10")
        ], start=1):
            var = tk.StringVar(value=default)
            setattr(parent, attr, var)
            ctk.CTkEntry(add_row, textvariable=var, placeholder_text=placeholder,
                         fg_color=SURFACE2, border_color=BORDER, text_color=TEXT,
                         height=26, width=44
                         ).grid(row=0, column=col, padx=2)

        def add_combatant():
            name = name_var.get().strip()
            if not name: return
            try:
                hp = int(getattr(parent,"_hp_var").get() or 10)
                ac = int(getattr(parent,"_ac_var").get() or 10)
                init_val = getattr(parent,"_init_var").get().strip()
                initiative = int(init_val) if init_val else dice_module.roll("1d20")["total"]
            except ValueError:
                return
            combatants.append({"name":name,"ac":ac,"max_hp":hp,"current_hp":hp,
                                "initiative":initiative,"conditions":[]})
            name_var.set("")
            getattr(parent,"_init_var").set("")
            _save_state(); _render_list()

        ctk.CTkButton(add_row, text="Add", width=44, height=26,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=TEXT,
                      font=ctk.CTkFont(size=11), command=add_combatant
                      ).grid(row=0, column=4, padx=(2,0))

    def _body_mechanics(self, parent, panel: dict):
        """Searchable mechanics list with inline expansion."""
        search_var = tk.StringVar()
        expanded: set[int] = set()

        search_row = ctk.CTkFrame(parent, fg_color="transparent")
        search_row.pack(fill="x", padx=6, pady=(4, 2))
        ctk.CTkEntry(search_row, textvariable=search_var, placeholder_text="Search mechanics…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=26
                     ).pack(fill="x")

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_button_color=ACCENT)
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        scroll.columnconfigure(0, weight=1)

        def _render(items=None):
            for w in scroll.winfo_children():
                w.destroy()
            items = items or self.db.list_mechanics(search=search_var.get().strip())
            for m in items[:60]:
                row = ctk.CTkFrame(scroll, fg_color=SURFACE2, corner_radius=4, cursor="hand2")
                row.pack(fill="x", padx=2, pady=1)
                row.columnconfigure(0, weight=1)
                icon = "▾" if m["id"] in expanded else "▸"
                hdr = ctk.CTkFrame(row, fg_color="transparent")
                hdr.grid(row=0, column=0, sticky="ew")
                hdr.columnconfigure(0, weight=1)
                ctk.CTkLabel(hdr, text=f"{icon}  {m['title']}", anchor="w",
                             text_color=TEXT, font=ctk.CTkFont(size=12)
                             ).grid(row=0, column=0, sticky="ew", padx=6, pady=4)
                if m.get("campaign"):
                    ctk.CTkLabel(hdr, text=m["campaign"], text_color=MUTED,
                                 font=ctk.CTkFont(size=10)
                                 ).grid(row=0, column=1, padx=(0,6))
                if m["id"] in expanded and m.get("body_md"):
                    md_w = MarkdownText(row, height=6, bg=SURFACE)
                    md_w.grid(row=1, column=0, sticky="ew", padx=6, pady=(0,4))
                    md_w.set_markdown(m["body_md"])

                def toggle(mid=m["id"]):
                    if mid in expanded:
                        expanded.discard(mid)
                    else:
                        expanded.add(mid)
                    _render()

                for w in (row, hdr):
                    w.bind("<Button-1>", lambda e, f=toggle: f())
                for child in hdr.winfo_children():
                    child.bind("<Button-1>", lambda e, f=toggle: f())

        search_var.trace_add("write", lambda *_: _render())
        _render()

    def _body_magic_items(self, parent, panel: dict):
        search_var = tk.StringVar()
        ctk.CTkEntry(parent, textvariable=search_var, placeholder_text="Search magic items…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=26
                     ).pack(fill="x", padx=6, pady=(4, 2))
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_button_color=ACCENT)
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        scroll.columnconfigure(0, weight=1)

        expanded: set[int] = set()

        def _render():
            for w in scroll.winfo_children():
                w.destroy()
            for it in self.db.list_items(search=search_var.get().strip())[:40]:
                color = RARITY_COLORS.get(it.get("rarity","Common"), MUTED)
                row = ctk.CTkFrame(scroll, fg_color=SURFACE2, corner_radius=4, cursor="hand2")
                row.pack(fill="x", padx=2, pady=1)
                row.columnconfigure(1, weight=1)
                ctk.CTkLabel(row, text="●", text_color=color,
                             font=ctk.CTkFont(size=10), width=14
                             ).grid(row=0, column=0, padx=(4,2), pady=4)
                ctk.CTkLabel(row, text=it["name"], anchor="w", text_color=TEXT,
                             font=ctk.CTkFont(size=12)
                             ).grid(row=0, column=1, sticky="ew", pady=4)
                ctk.CTkLabel(row, text=it.get("rarity",""), text_color=color,
                             font=ctk.CTkFont(size=10)
                             ).grid(row=0, column=2, padx=(0,6))

                if it["id"] in expanded:
                    desc = it.get("description","") or it.get("mechanical_effect","")
                    if desc:
                        md_w = MarkdownText(row, height=5, bg=SURFACE)
                        md_w.grid(row=1, column=0, columnspan=3, sticky="ew", padx=6, pady=(0,4))
                        md_w.set_markdown(desc)

                def toggle(mid=it["id"]):
                    if mid in expanded: expanded.discard(mid)
                    else: expanded.add(mid)
                    _render()

                row.bind("<Button-1>", lambda e, f=toggle: f())
                for c in row.winfo_children():
                    c.bind("<Button-1>", lambda e, f=toggle: f())

        search_var.trace_add("write", lambda *_: _render())
        _render()

    def _body_bestiary(self, parent, panel: dict):
        search_var = tk.StringVar()
        ctk.CTkEntry(parent, textvariable=search_var, placeholder_text="Search bestiary…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=26
                     ).pack(fill="x", padx=6, pady=(4, 2))
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_button_color=ACCENT)
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        scroll.columnconfigure(0, weight=1)

        expanded: set[int] = set()

        def _render():
            for w in scroll.winfo_children():
                w.destroy()
            for e in self.db.list_bestiary(search=search_var.get().strip())[:40]:
                row = ctk.CTkFrame(scroll, fg_color=SURFACE2, corner_radius=4, cursor="hand2")
                row.pack(fill="x", padx=2, pady=1)
                row.columnconfigure(0, weight=1)
                ctk.CTkLabel(row, text=e["name"], anchor="w", text_color=TEXT,
                             font=ctk.CTkFont(size=12)
                             ).grid(row=0, column=0, sticky="ew", padx=6, pady=4)
                ctk.CTkLabel(row, text=f"CR{e.get('cr','?')} AC{e.get('ac','?')} {e.get('max_hp','?')}HP",
                             text_color=MUTED, font=ctk.CTkFont(size=10)
                             ).grid(row=0, column=1, padx=(0,6))

                if e["id"] in expanded and e.get("statblock_md"):
                    md_w = MarkdownText(row, height=7,
                                        bg=SURFACE,
                                        font=("Consolas", 10),
                                        mono=("Consolas", 10))
                    md_w.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=(0,4))
                    md_w.set_markdown(e["statblock_md"])

                def toggle(eid=e["id"]):
                    if eid in expanded: expanded.discard(eid)
                    else: expanded.add(eid)
                    _render()

                row.bind("<Button-1>", lambda ev, f=toggle: f())
                for c in row.winfo_children():
                    c.bind("<Button-1>", lambda ev, f=toggle: f())

        search_var.trace_add("write", lambda *_: _render())
        _render()

    def _body_campaigns(self, parent, panel: dict):
        search_var = tk.StringVar()
        ctk.CTkEntry(parent, textvariable=search_var, placeholder_text="Search campaigns…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=26
                     ).pack(fill="x", padx=6, pady=(4, 2))
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_button_color=ACCENT)
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        scroll.columnconfigure(0, weight=1)

        expanded: set[int] = set()

        def _render():
            for w in scroll.winfo_children():
                w.destroy()
            for c in self.db.list_campaigns(search=search_var.get().strip())[:60]:
                row = ctk.CTkFrame(scroll, fg_color=SURFACE2, corner_radius=4, cursor="hand2")
                row.pack(fill="x", padx=2, pady=1)
                row.columnconfigure(0, weight=1)
                ctk.CTkLabel(row, text=c["title"], anchor="w", text_color=TEXT,
                             font=ctk.CTkFont(size=12)
                             ).grid(row=0, column=0, sticky="ew", padx=6, pady=4)

                if c["id"] in expanded and c.get("body_md"):
                    md_w = MarkdownText(row, height=6, bg=SURFACE)
                    md_w.grid(row=1, column=0, sticky="ew", padx=6, pady=(0,4))
                    md_w.set_markdown(c["body_md"])

                def toggle(cid=c["id"]):
                    if cid in expanded: expanded.discard(cid)
                    else: expanded.add(cid)
                    _render()

                row.bind("<Button-1>", lambda e, f=toggle: f())
                for child in row.winfo_children():
                    child.bind("<Button-1>", lambda e, f=toggle: f())

        search_var.trace_add("write", lambda *_: _render())
        _render()

    def _body_shops(self, parent, panel: dict):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_button_color=ACCENT)
        scroll.pack(fill="both", expand=True, padx=6, pady=(4, 6))
        scroll.columnconfigure(0, weight=1)

        shops: dict[str, list] = {}
        for it in self.db.list_shop_items():
            shops.setdefault(it["shop_name"], []).append(it)

        for shop_name, items in shops.items():
            ctk.CTkLabel(scroll, text=shop_name, text_color=ACCENT,
                         font=ctk.CTkFont(size=11, weight="bold"), anchor="w"
                         ).pack(fill="x", padx=4, pady=(6,1))
            for it in items:
                row = ctk.CTkFrame(scroll, fg_color=SURFACE2, corner_radius=3)
                row.pack(fill="x", padx=2, pady=1)
                row.columnconfigure(0, weight=1)
                ctk.CTkLabel(row, text=it["item_name"], anchor="w", text_color=TEXT,
                             font=ctk.CTkFont(size=11)
                             ).grid(row=0, column=0, sticky="ew", padx=6, pady=3)
                ctk.CTkLabel(row, text=f"{it.get('price','')}  ×{it.get('quantity',1)}",
                             text_color=MUTED, font=ctk.CTkFont(size=10)
                             ).grid(row=0, column=1, padx=(0,6))

        if not shops:
            ctk.CTkLabel(scroll, text="No shop items yet.", text_color=MUTED,
                         font=ctk.CTkFont(size=12)).pack(pady=20)

    def _body_party_items(self, parent, panel: dict):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_button_color=ACCENT)
        scroll.pack(fill="both", expand=True, padx=6, pady=(4, 6))
        scroll.columnconfigure(0, weight=1)

        owners: dict[str, list] = {}
        for it in self.db.list_party_items():
            owners.setdefault(it["owner"], []).append(it)

        for owner, items in owners.items():
            ctk.CTkLabel(scroll, text=owner, text_color=ACCENT,
                         font=ctk.CTkFont(size=11, weight="bold"), anchor="w"
                         ).pack(fill="x", padx=4, pady=(6,1))
            for it in items:
                row = ctk.CTkFrame(scroll, fg_color=SURFACE2, corner_radius=3)
                row.pack(fill="x", padx=2, pady=1)
                row.columnconfigure(0, weight=1)
                ctk.CTkLabel(row, text=f"{it['item_name']} ×{it.get('quantity',1)}",
                             anchor="w", text_color=TEXT, font=ctk.CTkFont(size=11)
                             ).grid(row=0, column=0, sticky="ew", padx=6, pady=3)

        if not owners:
            ctk.CTkLabel(scroll, text="No party loot yet.", text_color=MUTED,
                         font=ctk.CTkFont(size=12)).pack(pady=20)

    # ── Panel CRUD ─────────────────────────────────────────────────────────────

    def _new_panel(self):
        if not self._active_tab:
            return
        self._open_panel_editor(None)

    def _edit_panel(self, panel: dict):
        self._open_panel_editor(panel)

    def _open_panel_editor(self, panel: dict | None):
        is_new = panel is None
        ptype = panel.get("panel_type","text") if panel else "text"

        dlg = ctk.CTkToplevel(self)
        dlg.title("Add Panel" if is_new else "Edit Panel")
        dlg.geometry("560x520")
        dlg.configure(fg_color=SURFACE)
        dlg.grab_set()
        dlg.columnconfigure(0, weight=1)
        dlg.rowconfigure(4, weight=1)

        # Type picker
        ctk.CTkLabel(dlg, text="Panel Type", text_color=MUTED,
                     font=ctk.CTkFont(size=12), anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=16, pady=(14,2))

        type_var = tk.StringVar(value=ptype)
        type_grid = ctk.CTkFrame(dlg, fg_color=SURFACE2, corner_radius=6)
        type_grid.grid(row=1, column=0, sticky="ew", padx=16, pady=(0,8))

        for i, (key, label) in enumerate(PANEL_TYPES.items()):
            ctk.CTkRadioButton(
                type_grid, text=label, variable=type_var, value=key,
                text_color=TEXT, fg_color=ACCENT, hover_color=ACCENT_H,
                border_color=BORDER, font=ctk.CTkFont(size=12)
            ).grid(row=i//3, column=i%3, sticky="w", padx=12, pady=4)

        # Title
        title_row = ctk.CTkFrame(dlg, fg_color="transparent")
        title_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0,4))
        title_row.columnconfigure(1, weight=1)
        ctk.CTkLabel(title_row, text="Title", text_color=MUTED,
                     font=ctk.CTkFont(size=12), width=46, anchor="e"
                     ).grid(row=0, column=0, padx=(0,8))
        title_var = tk.StringVar(value=panel["title"] if panel else "")
        ctk.CTkEntry(title_row, textvariable=title_var, fg_color=SURFACE2,
                     border_color=BORDER, text_color=TEXT, height=30
                     ).grid(row=0, column=1, sticky="ew")

        # Size hint (panels are freely resized on the board by dragging)
        size_row = ctk.CTkFrame(dlg, fg_color="transparent")
        size_row.grid(row=3, column=0, sticky="ew", padx=16, pady=(0,4))
        if is_new:
            hint = "Size: drop a default panel, then drag its edges/corner to resize."
        else:
            cur = self._items.get(panel["id"])
            dims = f"{cur['w']}×{cur['h']} px" if cur else \
                   f"{panel.get('width_px', DEF_W)}×{panel.get('height_px', DEF_H)} px"
            hint = f"Size: {dims}  ·  drag the panel's edges/corner on the board to resize."
        ctk.CTkLabel(size_row, text=hint, text_color=MUTED,
                     font=ctk.CTkFont(size=11), anchor="w"
                     ).pack(side="left", padx=(0,8))

        # Content (only shown for text type)
        content_lbl = ctk.CTkLabel(dlg, text="Content", text_color=MUTED,
                                    font=ctk.CTkFont(size=12), anchor="w")
        content_lbl.grid(row=4, column=0, sticky="nw", padx=16, pady=(4,2))
        tb = ctk.CTkTextbox(dlg, fg_color=SURFACE2, border_color=BORDER,
                             text_color=TEXT, font=ctk.CTkFont(size=13), wrap="word")
        if panel and panel.get("panel_type","text") == "text":
            tb.insert("1.0", panel.get("content",""))
        tb.grid(row=5, column=0, sticky="nsew", padx=16, pady=(0,4))
        dlg.rowconfigure(5, weight=1)

        def on_type_change(*_):
            is_text = type_var.get() == "text"
            content_lbl.grid() if is_text else content_lbl.grid_remove()
            tb.grid() if is_text else tb.grid_remove()

        type_var.trace_add("write", on_type_change)
        on_type_change()

        # Auto-title from type if title is empty
        def auto_title(*_):
            if not title_var.get():
                label = PANEL_TYPES.get(type_var.get(),"").split("  ")[-1]
                title_var.set(label)
        type_var.trace_add("write", auto_title)

        ctk.CTkLabel(dlg, text="Tip: Resource panels pull live data from your DB — search, click to expand.",
                     text_color=MUTED, font=ctk.CTkFont(size=10)
                     ).grid(row=6, column=0, sticky="w", padx=16)

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.grid(row=7, column=0, sticky="ew", padx=16, pady=(6,14))

        def save():
            t = title_var.get().strip()
            if not t:
                messagebox.showerror("Validation","Title is required."); return
            c = tb.get("1.0","end").rstrip() if type_var.get()=="text" else ""
            pt = type_var.get()
            if is_new:
                x, y = self._next_panel_pos()
                self.db.create_dm_panel(self._active_tab["id"], t, c, 1, pt,
                                        pos_x=x, pos_y=y,
                                        width_px=DEF_W, height_px=DEF_H)
            else:
                self.db.update_dm_panel(panel["id"], t, c,
                                        panel.get("width", 1), pt)
            dlg.destroy()
            self._load_panels()

        ctk.CTkButton(btn_row, text="Cancel", width=90, height=34,
                      fg_color=SURFACE2, hover_color=BORDER, text_color=MUTED,
                      command=dlg.destroy).pack(side="right")
        ctk.CTkButton(btn_row, text="Save", width=90, height=34,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=TEXT,
                      command=save).pack(side="right", padx=(0,8))

    def _delete_panel(self, panel: dict):
        if messagebox.askyesno("Delete Panel", f"Delete '{panel['title']}'?"):
            self.db.delete_dm_panel(panel["id"])
            self._load_panels()

    # ── Canvas helpers ───────────────────────────────────────────────────────

    def _canvas_width(self) -> int:
        w = self._canvas.winfo_width()
        return w if w > 1 else 900

    def _update_scrollregion(self):
        items = list(self._items.values())
        if items:
            bottom = max(r["y"] + r["h"] for r in items) + MARGIN
            right  = max(r["x"] + r["w"] for r in items) + MARGIN
        else:
            bottom = right = 0
        height = max(bottom, self._canvas.winfo_height())
        width  = max(right, self._canvas_width())
        self._canvas.configure(scrollregion=(0, 0, width, height))

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-event.delta / 120), "units")

    def _raise_panel(self, pid: int):
        rec = self._items.get(pid)
        if rec:
            self._canvas.tag_raise(rec["item"])

    def _next_panel_pos(self) -> tuple[int, int]:
        """Cascade new panels so they don't perfectly overlap existing ones."""
        n = len(self._items)
        x = MARGIN + (n * 28) % max(1, (self._canvas_width() - DEF_W - MARGIN))
        y = MARGIN + (n * 28) % 360
        return int(x), int(y)

    # ── Move gesture ─────────────────────────────────────────────────────────

    def _move_start(self, event, pid: int):
        rec = self._items.get(pid)
        if not rec:
            return
        self._raise_panel(pid)
        self._gesture = {
            "pid": pid, "mode": "move",
            "mx": event.x_root, "my": event.y_root,
            "x0": rec["x"], "y0": rec["y"],
        }

    def _move_motion(self, event, pid: int):
        g = self._gesture
        if not g or g["pid"] != pid or g["mode"] != "move":
            return
        rec = self._items.get(pid)
        if not rec:
            return
        nx = max(0, g["x0"] + (event.x_root - g["mx"]))
        ny = max(0, g["y0"] + (event.y_root - g["my"]))
        rec["x"], rec["y"] = int(nx), int(ny)
        self._canvas.coords(rec["item"], rec["x"], rec["y"])

    # ── Resize gesture ───────────────────────────────────────────────────────

    def _resize_start(self, event, pid: int, mode: str):
        rec = self._items.get(pid)
        if not rec:
            return
        self._raise_panel(pid)
        self._gesture = {
            "pid": pid, "mode": "resize", "axis": mode,
            "mx": event.x_root, "my": event.y_root,
            "w0": rec["w"], "h0": rec["h"],
        }

    def _resize_motion(self, event, pid: int):
        g = self._gesture
        if not g or g["pid"] != pid or g["mode"] != "resize":
            return
        rec = self._items.get(pid)
        if not rec:
            return
        axis = g["axis"]
        new_w, new_h = rec["w"], rec["h"]
        if "w" in axis:
            new_w = max(MIN_W, g["w0"] + (event.x_root - g["mx"]))
        if "h" in axis:
            new_h = max(MIN_H, g["h0"] + (event.y_root - g["my"]))
        rec["w"], rec["h"] = int(new_w), int(new_h)
        self._canvas.itemconfigure(rec["item"], width=rec["w"], height=rec["h"])

    # ── Gesture end (shared) — persist + tidy scrollregion ────────────────────

    def _gesture_end(self, pid: int):
        g = self._gesture
        self._gesture = None
        rec = self._items.get(pid)
        if not rec:
            return
        self.db.update_dm_panel_geometry(pid, rec["x"], rec["y"], rec["w"], rec["h"])
        rec["panel"]["pos_x"]     = rec["x"]
        rec["panel"]["pos_y"]     = rec["y"]
        rec["panel"]["width_px"]  = rec["w"]
        rec["panel"]["height_px"] = rec["h"]
        self._update_scrollregion()

    # ── Layouts menu (presets + starters) ─────────────────────────────────────

    def _open_layouts_menu(self):
        if not self._active_tab:
            messagebox.showinfo("Layouts", "Create a tab first.")
            return
        menu = tk.Menu(self, tearoff=0, bg=SURFACE2, fg=TEXT,
                       activebackground=ACCENT, activeforeground=TEXT, bd=0)
        menu.add_command(label="Arrange: One Column",
                         command=lambda: self._apply_columns(1))
        menu.add_command(label="Arrange: Two Columns",
                         command=lambda: self._apply_columns(2))
        menu.add_command(label="Arrange: Three Columns",
                         command=lambda: self._apply_columns(3))
        menu.add_separator()
        menu.add_command(label="✨ Starter: Combat Screen",
                         command=lambda: self._apply_template("combat"))
        menu.add_command(label="✨ Starter: Session Prep",
                         command=lambda: self._apply_template("prep"))
        # Position near the Layouts button
        try:
            x = self.winfo_pointerx()
            y = self.winfo_pointery()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _apply_columns(self, n: int):
        """Masonry-arrange the current tab's panels into n columns."""
        if not self._panels:
            return
        cw = self._canvas_width()
        col_w = int((cw - 2 * MARGIN - (n - 1) * GAP) / n)
        col_w = max(MIN_W, col_w)
        col_y = [MARGIN] * n
        for panel in self._panels:
            c = min(range(n), key=lambda i: col_y[i])
            x = MARGIN + c * (col_w + GAP)
            y = col_y[c]
            h = max(MIN_H, panel.get("height_px", DEF_H))
            panel["pos_x"], panel["pos_y"] = x, y
            panel["width_px"], panel["height_px"] = col_w, h
            self.db.update_dm_panel_geometry(panel["id"], x, y, col_w, h)
            col_y[c] += h + GAP
        self._load_panels()

    def _apply_template(self, name: str):
        """Append a preset set of panels to the current tab, then arrange."""
        presets = {
            "combat": [
                ("⚔  Initiative",  "initiative"),
                ("☠  Bestiary",    "bestiary"),
                ("⚙  Mechanics",   "mechanics"),
                ("✎  Quick Notes", "notes"),
            ],
            "prep": [
                ("📖  Campaign Info", "campaigns"),
                ("✎  Quick Notes",   "notes"),
                ("✦  Magic Items",   "magic_items"),
                ("⚖  Shops",         "shops"),
            ],
        }
        items = presets.get(name)
        if not items:
            return
        for title, ptype in items:
            self.db.create_dm_panel(self._active_tab["id"], title, "", 1, ptype,
                                    pos_x=MARGIN, pos_y=MARGIN,
                                    width_px=DEF_W, height_px=DEF_H)
        # Reload then arrange into two columns for a tidy default
        self._panels = self.db.list_dm_panels(self._active_tab["id"])
        self._apply_columns(2)

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def refresh(self):
        tabs = self.db.list_dm_tabs()
        if self._active_tab and not any(t["id"]==self._active_tab["id"] for t in tabs):
            self._active_tab = None
        if self._active_tab is None and tabs:
            self._active_tab = tabs[0]
        self._render_tabs()
        self._load_panels()
