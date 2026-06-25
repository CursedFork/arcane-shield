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


class DmShieldPage(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._active_tab: dict | None = None
        self._panels: list[dict] = []

        # Drag state
        self._drag_id: int | None = None
        self._drag_source_idx: int = 0
        self._drag_ghost: tk.Toplevel | None = None
        self._drag_over_idx: int | None = None
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self._panel_widgets: list[ctk.CTkFrame] = []

        self._build()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._tab_bar = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8, height=46)
        self._tab_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 4))
        self._tab_bar.grid_propagate(False)

        self._tab_inner = ctk.CTkFrame(self._tab_bar, fg_color="transparent")
        self._tab_inner.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        ctk.CTkButton(
            self._tab_bar, text="+ Tab", width=72, height=30,
            fg_color="transparent", hover_color=SURFACE2,
            text_color=MUTED, font=ctk.CTkFont(size=12),
            command=self._new_tab
        ).pack(side="right", padx=(0, 8), pady=8)

        self._canvas_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", scrollbar_button_color=ACCENT
        )
        self._canvas_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))
        self._canvas_frame.columnconfigure((0, 1, 2), weight=1)

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
        self._render_panels(self._panels)

    def _render_panels(self, panels: list[dict]):
        for w in self._canvas_frame.winfo_children():
            w.destroy()
        self._panel_widgets = []

        if not self._active_tab:
            ctk.CTkLabel(
                self._canvas_frame,
                text="No tabs yet — click  + Tab  to create your first DM screen.",
                text_color=MUTED, font=ctk.CTkFont(size=14)
            ).grid(row=0, column=0, columnspan=3, pady=60)
            return

        ctk.CTkButton(
            self._canvas_frame, text="+ Add Panel", height=36,
            fg_color=SURFACE, hover_color=SURFACE2, text_color=MUTED,
            font=ctk.CTkFont(size=13), border_color=BORDER, border_width=2,
            corner_radius=8, command=self._new_panel
        ).grid(row=0, column=0, columnspan=3, sticky="ew", padx=4, pady=(4, 8))

        if not panels:
            ctk.CTkLabel(
                self._canvas_frame,
                text="No panels yet — click  + Add Panel  to build your DM screen.",
                text_color=MUTED, font=ctk.CTkFont(size=13)
            ).grid(row=1, column=0, columnspan=3, pady=40)
            return

        col, row = 0, 1
        for idx, panel in enumerate(panels):
            span = min(panel.get("width", 1), 3)
            if col + span > 3:
                col = 0; row += 1
            widget = self._make_panel_widget(panel, idx)
            widget.grid(row=row, column=col, columnspan=span,
                        sticky="nsew", padx=4, pady=4)
            self._panel_widgets.append(widget)
            col += span
            if col >= 3:
                col = 0; row += 1

    # ── Panel shell (header + drag) ────────────────────────────────────────────

    def _make_panel_widget(self, panel: dict, idx: int) -> ctk.CTkFrame:
        ptype = panel.get("panel_type", "text")
        outer = ctk.CTkFrame(self._canvas_frame, fg_color=SURFACE,
                              corner_radius=8, border_color=BORDER, border_width=1)
        outer._panel_id = panel["id"]
        outer._panel_idx = idx

        # Header
        header = ctk.CTkFrame(outer, fg_color=SURFACE2, corner_radius=0, height=34)
        header.pack(fill="x")
        header.pack_propagate(False)

        grip = ctk.CTkLabel(header, text="⠿", text_color=MUTED,
                             font=ctk.CTkFont(size=16), width=24, cursor="fleur")
        grip.pack(side="left", padx=(6, 2))

        type_icon = PANEL_TYPES.get(ptype, "📝  Custom Text").split("  ")[0]
        ctk.CTkLabel(header, text=f"{type_icon}  {panel['title']}", anchor="w",
                     text_color=TEXT, font=ctk.CTkFont(size=13, weight="bold")
                     ).pack(side="left", fill="x", expand=True, padx=4)

        w_labels = {1: "↔ Wide", 2: "↔ Full", 3: "↕ Narrow"}
        ctk.CTkButton(header, text=w_labels.get(panel.get("width", 1), "↔ Wide"),
                      width=72, height=24, fg_color="transparent", hover_color=SURFACE,
                      text_color=MUTED, font=ctk.CTkFont(size=10),
                      command=lambda p=panel: self._toggle_width(p)
                      ).pack(side="right", padx=2)
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

        # Body — dispatch to panel type renderer
        body = ctk.CTkFrame(outer, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=0, pady=0)

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

        # Drag bindings on grip + header bg
        for w in (grip, header):
            w.bind("<ButtonPress-1>",  lambda e, p=panel, o=outer: self._drag_start(e, p, o))
            w.bind("<B1-Motion>",       self._drag_motion)
            w.bind("<ButtonRelease-1>", self._drag_end)

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
                                         height=120, scrollbar_button_color=ACCENT)
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
                                             height=130, scrollbar_button_color=ACCENT)
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
                                         height=180, scrollbar_button_color=ACCENT)
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        scroll.columnconfigure(0, weight=1)

        def _render(items=None):
            for w in scroll.winfo_children():
                w.destroy()
            items = items or self.db.list_mechanics(search=search_var.get().strip())
            for m in items:
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
                                         height=180, scrollbar_button_color=ACCENT)
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
                                         height=180, scrollbar_button_color=ACCENT)
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
                                         height=180, scrollbar_button_color=ACCENT)
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        scroll.columnconfigure(0, weight=1)

        expanded: set[int] = set()

        def _render():
            for w in scroll.winfo_children():
                w.destroy()
            for c in self.db.list_campaigns(search=search_var.get().strip()):
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
                                         height=200, scrollbar_button_color=ACCENT)
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
                                         height=200, scrollbar_button_color=ACCENT)
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

        # Width
        width_row = ctk.CTkFrame(dlg, fg_color="transparent")
        width_row.grid(row=3, column=0, sticky="ew", padx=16, pady=(0,4))
        ctk.CTkLabel(width_row, text="Width", text_color=MUTED,
                     font=ctk.CTkFont(size=12), width=46, anchor="e"
                     ).pack(side="left", padx=(0,8))
        width_var = tk.StringVar(value=str(panel.get("width",1) if panel else 1))
        for lbl, val in [("Narrow (1 col)","1"), ("Wide (2 col)","2"), ("Full (3 col)","3")]:
            ctk.CTkRadioButton(width_row, text=lbl, variable=width_var, value=val,
                               text_color=TEXT, fg_color=ACCENT, hover_color=ACCENT_H,
                               border_color=BORDER, font=ctk.CTkFont(size=12)
                               ).pack(side="left", padx=8)

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
            w = int(width_var.get())
            pt = type_var.get()
            if is_new:
                self.db.create_dm_panel(self._active_tab["id"], t, c, w, pt)
            else:
                self.db.update_dm_panel(panel["id"], t, c, w, pt)
            dlg.destroy()
            self._load_panels()

        ctk.CTkButton(btn_row, text="Cancel", width=90, height=34,
                      fg_color=SURFACE2, hover_color=BORDER, text_color=MUTED,
                      command=dlg.destroy).pack(side="right")
        ctk.CTkButton(btn_row, text="Save", width=90, height=34,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=TEXT,
                      command=save).pack(side="right", padx=(0,8))

    def _toggle_width(self, panel: dict):
        new_width = (panel.get("width",1) % 3) + 1
        self.db.update_dm_panel(panel["id"], panel["title"],
                                panel.get("content",""), new_width,
                                panel.get("panel_type","text"))
        self._load_panels()

    def _delete_panel(self, panel: dict):
        if messagebox.askyesno("Delete Panel", f"Delete '{panel['title']}'?"):
            self.db.delete_dm_panel(panel["id"])
            self._load_panels()

    # ── Drag and drop ──────────────────────────────────────────────────────────

    def _drag_start(self, event, panel: dict, outer: ctk.CTkFrame):
        self._drag_id = panel["id"]
        self._drag_source_idx = next(
            (i for i,p in enumerate(self._panels) if p["id"]==panel["id"]), 0)
        self._drag_offset_x = event.x
        self._drag_offset_y = event.y

        self._drag_ghost = tk.Toplevel(self)
        self._drag_ghost.overrideredirect(True)
        self._drag_ghost.attributes("-alpha", 0.75)
        self._drag_ghost.attributes("-topmost", True)
        self._drag_ghost.configure(bg=GHOST_BG)
        tk.Label(self._drag_ghost, text=f"  {panel['title']}  ",
                 bg=GHOST_BG, fg=TEXT, font=("Segoe UI",12,"bold"),
                 padx=12, pady=8).pack()
        self._move_ghost(event)

    def _drag_motion(self, event):
        if not self._drag_ghost: return
        self._move_ghost(event)
        target = self._find_panel_at(event.x_root, event.y_root)
        for i, w in enumerate(self._panel_widgets):
            if i == self._drag_source_idx:
                w.configure(fg_color=SURFACE, border_color=BORDER)
            elif i == target:
                w.configure(fg_color=DRAG_HL, border_color=ACCENT)
            else:
                w.configure(fg_color=SURFACE, border_color=BORDER)
        self._drag_over_idx = target

    def _move_ghost(self, event):
        x = event.x_root - self._drag_offset_x + 10
        y = event.y_root - self._drag_offset_y + 10
        self._drag_ghost.geometry(f"+{x}+{y}")

    def _find_panel_at(self, rx, ry) -> int | None:
        for i, w in enumerate(self._panel_widgets):
            try:
                if (w.winfo_rootx() <= rx <= w.winfo_rootx() + w.winfo_width() and
                        w.winfo_rooty() <= ry <= w.winfo_rooty() + w.winfo_height()):
                    return i
            except Exception:
                pass
        return None

    def _drag_end(self, event):
        if self._drag_ghost:
            self._drag_ghost.destroy()
            self._drag_ghost = None

        for w in self._panel_widgets:
            w.configure(fg_color=SURFACE, border_color=BORDER)

        if self._drag_over_idx is not None and self._drag_over_idx != self._drag_source_idx:
            panels = list(self._panels)
            panel = panels.pop(self._drag_source_idx)
            panels.insert(self._drag_over_idx, panel)
            self._panels = panels
            self.db.reorder_dm_panels([p["id"] for p in panels])
            self._render_panels(self._panels)

        self._drag_id = None

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def refresh(self):
        tabs = self.db.list_dm_tabs()
        if self._active_tab and not any(t["id"]==self._active_tab["id"] for t in tabs):
            self._active_tab = None
        if self._active_tab is None and tabs:
            self._active_tab = tabs[0]
        self._render_tabs()
        self._load_panels()
