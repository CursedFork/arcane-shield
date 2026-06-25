"""DM Shield page — customizable reference screen with draggable panels and user-defined tabs."""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog

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
DRAG_HL  = "#3d2f5e"   # panel highlight while dragging over it
GHOST_BG = "#4a3580"   # floating ghost colour


class DmShieldPage(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._active_tab: dict | None = None
        self._panels: list[dict] = []

        # Drag state
        self._drag_id: int | None = None        # panel id being dragged
        self._drag_ghost: tk.Toplevel | None = None
        self._drag_over_idx: int | None = None  # index we're hovering over
        self._panel_widgets: list[ctk.CTkFrame] = []

        self._build()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Tab bar ────────────────────────────────────────────────────────────
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

        # ── Panel grid ─────────────────────────────────────────────────────────
        self._canvas_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", scrollbar_button_color=ACCENT
        )
        self._canvas_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))
        self._canvas_frame.columnconfigure((0, 1, 2), weight=1)

        # Empty state
        self._empty_lbl = ctk.CTkLabel(
            self._canvas_frame,
            text="No tabs yet.\nClick  + Tab  above to create your first DM reference screen.",
            text_color=MUTED, font=ctk.CTkFont(size=14), justify="center"
        )

    # ── Tab bar rendering ──────────────────────────────────────────────────────

    def _render_tabs(self):
        for w in self._tab_inner.winfo_children():
            w.destroy()

        tabs = self.db.list_dm_tabs()

        for tab in tabs:
            is_active = self._active_tab and tab["id"] == self._active_tab["id"]
            btn = ctk.CTkButton(
                self._tab_inner,
                text=tab["name"],
                height=30,
                fg_color=ACCENT if is_active else "transparent",
                hover_color=ACCENT_H if is_active else SURFACE2,
                text_color=TEXT if is_active else MUTED,
                font=ctk.CTkFont(size=13),
                corner_radius=6,
                command=lambda t=tab: self._switch_tab(t)
            )
            btn.pack(side="left", padx=(0, 2))

            # Right-click to rename/delete
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
        if new_tab:
            self._switch_tab(new_tab)
        else:
            self._render_tabs()

    def _rename_tab(self, tab: dict):
        name = simpledialog.askstring("Rename Tab", "New name:", initialvalue=tab["name"], parent=self)
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

    # ── Panel loading & rendering ──────────────────────────────────────────────

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
            self._empty_lbl = ctk.CTkLabel(
                self._canvas_frame,
                text="No tabs yet.\nClick  + Tab  above to create your first DM reference screen.",
                text_color=MUTED, font=ctk.CTkFont(size=14), justify="center"
            )
            self._empty_lbl.grid(row=0, column=0, columnspan=3, pady=60)
            return

        # "Add panel" button always first
        add_btn = ctk.CTkButton(
            self._canvas_frame,
            text="+ Add Panel",
            height=36, fg_color=SURFACE, hover_color=SURFACE2,
            text_color=MUTED, font=ctk.CTkFont(size=13),
            border_color=BORDER, border_width=2, corner_radius=8,
            command=self._new_panel
        )
        add_btn.grid(row=0, column=0, columnspan=3, sticky="ew", padx=4, pady=(4, 8))

        if not panels:
            ctk.CTkLabel(
                self._canvas_frame,
                text="No panels yet — click  + Add Panel  to start building your DM screen.",
                text_color=MUTED, font=ctk.CTkFont(size=13)
            ).grid(row=1, column=0, columnspan=3, pady=40)
            return

        # Lay out panels: each panel is 1 or 2 columns wide in a 3-column grid
        col = 0
        row = 1
        for idx, panel in enumerate(panels):
            span = min(panel.get("width", 1), 3)
            if col + span > 3:
                col = 0
                row += 1

            widget = self._make_panel_widget(panel, idx)
            widget.grid(row=row, column=col, columnspan=span,
                        sticky="nsew", padx=4, pady=4)
            self._panel_widgets.append(widget)
            self._canvas_frame.grid_rowconfigure(row, weight=0)

            col += span
            if col >= 3:
                col = 0
                row += 1

    def _make_panel_widget(self, panel: dict, idx: int) -> ctk.CTkFrame:
        outer = ctk.CTkFrame(self._canvas_frame, fg_color=SURFACE,
                              corner_radius=8, border_color=BORDER, border_width=1)
        outer._panel_id = panel["id"]
        outer._panel_idx = idx

        # Header bar (drag handle)
        header = ctk.CTkFrame(outer, fg_color=SURFACE2, corner_radius=0, height=34)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Drag grip
        grip = ctk.CTkLabel(header, text="⠿", text_color=MUTED,
                             font=ctk.CTkFont(size=16), width=24, cursor="fleur")
        grip.pack(side="left", padx=(6, 2))

        ctk.CTkLabel(header, text=panel["title"], anchor="w",
                     text_color=TEXT, font=ctk.CTkFont(size=13, weight="bold")
                     ).pack(side="left", fill="x", expand=True, padx=4)

        # Width toggle
        w_lbl = "↔ Wide" if panel.get("width", 1) == 1 else "↕ Narrow"
        ctk.CTkButton(header, text=w_lbl, width=72, height=24,
                      fg_color="transparent", hover_color=SURFACE,
                      text_color=MUTED, font=ctk.CTkFont(size=10),
                      command=lambda p=panel: self._toggle_width(p)
                      ).pack(side="right", padx=2)

        ctk.CTkButton(header, text="✎", width=28, height=24,
                      fg_color="transparent", hover_color=SURFACE,
                      text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=lambda p=panel: self._edit_panel(p)
                      ).pack(side="right")

        ctk.CTkButton(header, text="✕", width=28, height=24,
                      fg_color="transparent", hover_color=DANGER,
                      text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=lambda p=panel: self._delete_panel(p)
                      ).pack(side="right")

        # Content
        content_text = panel.get("content", "") or "(empty)"
        tb = ctk.CTkTextbox(outer, fg_color=SURFACE, text_color=TEXT,
                             border_width=0, font=ctk.CTkFont(size=12),
                             wrap="word", height=140)
        tb.insert("1.0", panel.get("content", ""))
        tb.configure(state="disabled")
        tb.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        # Bind drag events to grip + header
        for widget in (grip, header):
            widget.bind("<ButtonPress-1>",   lambda e, p=panel, o=outer: self._drag_start(e, p, o))
            widget.bind("<B1-Motion>",        self._drag_motion)
            widget.bind("<ButtonRelease-1>",  self._drag_end)

        return outer

    # ── Drag and drop ──────────────────────────────────────────────────────────

    def _drag_start(self, event, panel: dict, outer: ctk.CTkFrame):
        self._drag_id = panel["id"]
        self._drag_source_idx = self._panels.index(panel)

        # Create ghost window
        self._drag_ghost = tk.Toplevel(self)
        self._drag_ghost.overrideredirect(True)
        self._drag_ghost.attributes("-alpha", 0.75)
        self._drag_ghost.attributes("-topmost", True)
        self._drag_ghost.configure(bg=GHOST_BG)

        ghost_lbl = tk.Label(
            self._drag_ghost,
            text=f"  {panel['title']}  ",
            bg=GHOST_BG, fg=TEXT,
            font=("Segoe UI", 12, "bold"),
            padx=12, pady=8
        )
        ghost_lbl.pack()

        self._drag_offset_x = event.x
        self._drag_offset_y = event.y
        self._move_ghost(event)

    def _drag_motion(self, event):
        if not self._drag_ghost:
            return
        self._move_ghost(event)
        self._update_drop_highlight(event)

    def _move_ghost(self, event):
        x = event.x_root - self._drag_offset_x + 10
        y = event.y_root - self._drag_offset_y + 10
        self._drag_ghost.geometry(f"+{x}+{y}")

    def _update_drop_highlight(self, event):
        """Highlight whichever panel the cursor is over."""
        target_idx = self._find_panel_at(event.x_root, event.y_root)

        # Clear previous highlight
        for i, w in enumerate(self._panel_widgets):
            if i == self._drag_source_idx:
                w.configure(fg_color=SURFACE, border_color=BORDER)
            elif i == target_idx:
                w.configure(fg_color=DRAG_HL, border_color=ACCENT)
            else:
                w.configure(fg_color=SURFACE, border_color=BORDER)

        self._drag_over_idx = target_idx

    def _find_panel_at(self, root_x: int, root_y: int) -> int | None:
        """Return index of the panel widget the mouse is over."""
        for i, w in enumerate(self._panel_widgets):
            try:
                wx = w.winfo_rootx()
                wy = w.winfo_rooty()
                ww = w.winfo_width()
                wh = w.winfo_height()
                if wx <= root_x <= wx + ww and wy <= root_y <= wy + wh:
                    return i
            except Exception:
                pass
        return None

    def _drag_end(self, event):
        if self._drag_ghost:
            self._drag_ghost.destroy()
            self._drag_ghost = None

        # Reset highlight
        for w in self._panel_widgets:
            w.configure(fg_color=SURFACE, border_color=BORDER)

        if self._drag_over_idx is None or self._drag_over_idx == self._drag_source_idx:
            self._drag_id = None
            return

        # Reorder: move dragged panel to the drop position
        panels = list(self._panels)
        src = self._drag_source_idx
        dst = self._drag_over_idx

        panel = panels.pop(src)
        panels.insert(dst, panel)
        self._panels = panels

        # Persist new order
        self.db.reorder_dm_panels([p["id"] for p in panels])
        self._render_panels(self._panels)
        self._drag_id = None

    # ── Panel CRUD ─────────────────────────────────────────────────────────────

    def _new_panel(self):
        if not self._active_tab:
            return
        self._open_panel_editor(None)

    def _edit_panel(self, panel: dict):
        self._open_panel_editor(panel)

    def _open_panel_editor(self, panel: dict | None):
        is_new = panel is None
        dlg = ctk.CTkToplevel(self)
        dlg.title("New Panel" if is_new else "Edit Panel")
        dlg.geometry("600x520")
        dlg.configure(fg_color=SURFACE)
        dlg.grab_set()
        dlg.columnconfigure(0, weight=1)
        dlg.rowconfigure(2, weight=1)

        # Title
        title_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 4))
        title_frame.columnconfigure(1, weight=1)
        ctk.CTkLabel(title_frame, text="Title", text_color=MUTED,
                     font=ctk.CTkFont(size=12), width=50, anchor="e"
                     ).grid(row=0, column=0, padx=(0, 8))
        title_var = tk.StringVar(value=panel["title"] if panel else "")
        ctk.CTkEntry(title_frame, textvariable=title_var, fg_color=SURFACE2,
                     border_color=BORDER, text_color=TEXT, height=32
                     ).grid(row=0, column=1, sticky="ew")

        # Width
        width_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        width_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))
        ctk.CTkLabel(width_frame, text="Width", text_color=MUTED,
                     font=ctk.CTkFont(size=12), width=50, anchor="e"
                     ).pack(side="left", padx=(0, 8))
        width_var = tk.StringVar(value=str(panel.get("width", 1) if panel else 1))
        for label, val in [("Narrow (1 col)", "1"), ("Wide (2 col)", "2"), ("Full (3 col)", "3")]:
            ctk.CTkRadioButton(width_frame, text=label, variable=width_var, value=val,
                               text_color=TEXT, fg_color=ACCENT,
                               hover_color=ACCENT_H, border_color=BORDER
                               ).pack(side="left", padx=8)

        # Content
        ctk.CTkLabel(dlg, text="Content", text_color=MUTED,
                     font=ctk.CTkFont(size=12), anchor="w"
                     ).grid(row=2, column=0, sticky="nw", padx=16, pady=(4, 2))
        tb = ctk.CTkTextbox(dlg, fg_color=SURFACE2, border_color=BORDER,
                             text_color=TEXT, font=ctk.CTkFont(size=13), wrap="word")
        tb.insert("1.0", panel.get("content", "") if panel else "")
        tb.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 8))
        dlg.rowconfigure(3, weight=1)

        ctk.CTkLabel(dlg, text="Tip: paste any reference text — AC tables, spell descriptions, house rules…",
                     text_color=MUTED, font=ctk.CTkFont(size=10)
                     ).grid(row=4, column=0, sticky="w", padx=16)

        # Buttons
        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.grid(row=5, column=0, sticky="ew", padx=16, pady=(8, 16))

        def save():
            t = title_var.get().strip()
            if not t:
                messagebox.showerror("Validation", "Title is required."); return
            c = tb.get("1.0", "end").rstrip()
            w = int(width_var.get())
            if is_new:
                self.db.create_dm_panel(self._active_tab["id"], t, c, w)
            else:
                self.db.update_dm_panel(panel["id"], t, c, w)
            dlg.destroy()
            self._load_panels()

        ctk.CTkButton(btn_row, text="Cancel", width=90, height=34,
                      fg_color=SURFACE2, hover_color=BORDER, text_color=MUTED,
                      command=dlg.destroy).pack(side="right")
        ctk.CTkButton(btn_row, text="Save", width=90, height=34,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=TEXT,
                      command=save).pack(side="right", padx=(0, 8))

    def _toggle_width(self, panel: dict):
        new_width = (panel.get("width", 1) % 3) + 1
        self.db.update_dm_panel(panel["id"], panel["title"], panel.get("content",""), new_width)
        self._load_panels()

    def _delete_panel(self, panel: dict):
        if messagebox.askyesno("Delete Panel", f"Delete '{panel['title']}'?"):
            self.db.delete_dm_panel(panel["id"])
            self._load_panels()

    # ── Page lifecycle ─────────────────────────────────────────────────────────

    def refresh(self):
        tabs = self.db.list_dm_tabs()

        # If active tab was deleted externally, reset
        if self._active_tab and not any(t["id"] == self._active_tab["id"] for t in tabs):
            self._active_tab = None

        if self._active_tab is None and tabs:
            self._active_tab = tabs[0]

        self._render_tabs()
        self._load_panels()
