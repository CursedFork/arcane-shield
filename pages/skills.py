"""Skill Checks page — the 18 standard skills, their ability, and uses."""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from pages.md_widget import MarkdownText
from pages.ui_util import bind_row, ScrollList

BG       = "#0f0f13"
SURFACE  = "#1a1a24"
SURFACE2 = "#22222f"
BORDER   = "#2e2e3e"
ACCENT   = "#7c5cbf"
ACCENT_H = "#9472d8"
TEXT     = "#e2e0f0"
MUTED    = "#8a8aa0"
DANGER   = "#c0392b"

ABILITIES = ["Strength", "Dexterity", "Constitution",
             "Intelligence", "Wisdom", "Charisma"]
ABILITY_COLORS = {
    "Strength": "#e74c3c", "Dexterity": "#2ecc71", "Constitution": "#e67e22",
    "Intelligence": "#3498db", "Wisdom": "#9b59b6", "Charisma": "#f1c40f",
}

# Typical DC guidance shown alongside the skill list (DMG difficulty bands).
DC_GUIDE = ("**Typical DCs** — Very easy 5 · Easy 10 · Medium 15 · "
            "Hard 20 · Very hard 25 · Nearly impossible 30")


class SkillsPage(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._items: list[dict] = []
        self._debounce_id = None
        self._build()

    def _debounce(self, fn, ms=160):
        if self._debounce_id is not None:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(ms, fn)

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self, width=260, fg_color=SURFACE, corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(16,8), pady=16)
        left.grid_propagate(False)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,6))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="Skill Checks", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="+ New", width=60, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._new).grid(row=0, column=1, sticky="e")

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._debounce(self._apply))
        ctk.CTkEntry(left, textvariable=self._search_var, placeholder_text="Search…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=30
                     ).grid(row=1, column=0, sticky="ew", padx=12, pady=(0,6))

        self._list_frame = ScrollList(left, bg=SURFACE, accent=ACCENT)
        self._list_frame.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0,12))

        self._right = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        self._right.grid(row=0, column=1, sticky="nsew", padx=(8,16), pady=16)
        self._right.grid_columnconfigure(0, weight=1)
        self._right.grid_rowconfigure(1, weight=1)
        self._show_placeholder()

    def _render_list(self):
        body = self._list_frame.body
        self._list_frame.clear()
        for it in self._items:
            color = ABILITY_COLORS.get(it.get("ability", ""), MUTED)
            row = tk.Frame(body, bg=SURFACE, cursor="hand2")
            row.pack(fill="x", padx=2, pady=1)
            tk.Label(row, text=(it.get("ability", "")[:3].upper() or "—"), fg=color, bg=SURFACE,
                     width=4, font=("Segoe UI", 8, "bold")).pack(side="right", padx=6)
            tk.Label(row, text=it["name"], anchor="w", fg=TEXT, bg=SURFACE,
                     font=("Segoe UI", 11)).pack(side="left", fill="x", expand=True,
                                                 padx=8, pady=6)
            bind_row(row, lambda x=it: self._show_detail(x), SURFACE, SURFACE2)
        self._list_frame.finalize()

    def refresh(self):
        self._apply()

    def _apply(self):
        self._items = self.db.list_skills(search=self._search_var.get().strip())
        self._render_list()

    def _show_placeholder(self):
        for w in self._right.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._right, text="Select a skill to view it",
                     text_color=MUTED, font=ctk.CTkFont(size=13)).pack(expand=True, pady=(40,4))
        guide = MarkdownText(self._right, height=3, bg=SURFACE)
        guide.pack(fill="x", padx=24, pady=8)
        guide.set_markdown(DC_GUIDE)

    def _show_detail(self, it: dict):
        for w in self._right.winfo_children():
            w.destroy()
        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text=it["name"], font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT, anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(hdr, text=it.get("ability", ""),
                     text_color=ABILITY_COLORS.get(it.get("ability",""), MUTED),
                     font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
                     ).grid(row=1, column=0, sticky="w")
        btns = ctk.CTkFrame(hdr, fg_color="transparent")
        btns.grid(row=0, column=1, rowspan=2, sticky="ne")
        ctk.CTkButton(btns, text="Edit", width=64, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=lambda: self._show_edit(it)).pack(side="left", padx=(0,4))
        ctk.CTkButton(btns, text="Delete", width=64, height=28, fg_color=DANGER,
                      hover_color="#e74c3c", text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=lambda: self._delete(it)).pack(side="left")
        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        md = MarkdownText(self._right, bg=SURFACE2)
        md.pack(fill="both", expand=True, padx=16, pady=(0,8))
        md.set_markdown(it.get("description", "") or "*(no description)*")

        guide = MarkdownText(self._right, height=2, bg=SURFACE)
        guide.pack(fill="x", padx=16, pady=(0,12))
        guide.set_markdown(DC_GUIDE)

    def _new(self):
        self._show_edit({})

    def _show_edit(self, it: dict):
        for w in self._right.winfo_children():
            w.destroy()
        is_new = not it.get("id")
        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        ctk.CTkLabel(hdr, text="New Skill" if is_new else f"Edit: {it.get('name','')}",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT, anchor="w"
                     ).pack(side="left")
        ctk.CTkButton(hdr, text="Cancel", width=72, height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=lambda: (self._show_detail(it) if not is_new else self._show_placeholder())
                      ).pack(side="right")

        name_var = tk.StringVar(value=it.get("name", ""))
        ability_var = tk.StringVar(value=it.get("ability", "") or ABILITIES[0])

        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Validation", "Name is required."); return
            data = {"name": name, "ability": ability_var.get(),
                    "description": desc.get("1.0", "end").rstrip()}
            if it.get("id"):
                self.db.update_skill(it["id"], data)
            else:
                self.db.create_skill(data)
            self.refresh()
            saved = next((x for x in self._items if x["name"] == name), None)
            if saved:
                self._show_detail(saved)

        ctk.CTkButton(hdr, text="Save", width=72, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=save).pack(side="right", padx=(0,6))
        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        form = ctk.CTkFrame(self._right, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=12, pady=(0,12))
        form.columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text="Name", text_color=MUTED, font=ctk.CTkFont(size=12),
                     width=80, anchor="e").grid(row=0, column=0, sticky="e", padx=(8,4), pady=3)
        ctk.CTkEntry(form, textvariable=name_var, fg_color=SURFACE2, border_color=BORDER,
                     text_color=TEXT, height=28).grid(row=0, column=1, sticky="ew", pady=3)
        ctk.CTkLabel(form, text="Ability", text_color=MUTED, font=ctk.CTkFont(size=12),
                     width=80, anchor="e").grid(row=1, column=0, sticky="e", padx=(8,4), pady=3)
        ctk.CTkOptionMenu(form, variable=ability_var, values=ABILITIES, fg_color=SURFACE2,
                          button_color=ACCENT, button_hover_color=ACCENT_H, text_color=TEXT
                          ).grid(row=1, column=1, sticky="w", pady=3)
        ctk.CTkLabel(form, text="Description", text_color=MUTED, font=ctk.CTkFont(size=12),
                     width=80, anchor="ne").grid(row=2, column=0, sticky="ne", padx=(8,4), pady=3)
        desc = ctk.CTkTextbox(form, fg_color=SURFACE2, border_color=BORDER, text_color=TEXT,
                              font=ctk.CTkFont(size=13), wrap="word")
        desc.insert("1.0", it.get("description", ""))
        desc.grid(row=2, column=1, sticky="nsew", pady=3)
        form.rowconfigure(2, weight=1)

    def _delete(self, it: dict):
        if messagebox.askyesno("Delete", f"Delete '{it['name']}'?"):
            self.db.delete_skill(it["id"])
            self.refresh()
            self._show_placeholder()
