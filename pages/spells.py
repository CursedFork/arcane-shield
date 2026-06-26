"""Spells page — searchable spellbook with level/school/class filters."""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
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

SCHOOLS = ["Abjuration", "Conjuration", "Divination", "Enchantment",
           "Evocation", "Illusion", "Necromancy", "Transmutation"]
CLASSES = ["Artificer", "Bard", "Cleric", "Druid", "Paladin",
           "Ranger", "Sorcerer", "Warlock", "Wizard"]
LEVELS = ["Cantrip"] + [str(i) for i in range(1, 10)]

SCHOOL_COLORS = {
    "Abjuration": "#5dade2", "Conjuration": "#f5b041", "Divination": "#aab7b8",
    "Enchantment": "#ec7063", "Evocation": "#e74c3c", "Illusion": "#bb8fce",
    "Necromancy": "#52be80", "Transmutation": "#48c9b0",
}


def _lvl_label(lv: int) -> str:
    return "Cantrip" if lv == 0 else f"Level {lv}"


class SpellsPage(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._spells: list[dict] = []
        self._selected: dict | None = None
        self._debounce_id = None
        self._build()

    def _debounce(self, fn, ms=160):
        if self._debounce_id is not None:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(ms, fn)

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Left panel ───────────────────────────────────────────────────────
        left = ctk.CTkFrame(self, width=300, fg_color=SURFACE, corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(16,8), pady=16)
        left.grid_propagate(False)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,6))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="Spells", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="+ New", width=64, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._new).grid(row=0, column=1, sticky="e")
        ctk.CTkButton(hdr, text="Clear All", width=72, height=28,
                      fg_color="transparent", hover_color=DANGER, text_color=MUTED,
                      font=ctk.CTkFont(size=12),
                      command=self._clear_all).grid(row=0, column=2, sticky="e", padx=(4,0))

        # Filters
        flt = ctk.CTkFrame(left, fg_color="transparent")
        flt.grid(row=1, column=0, sticky="ew", padx=12, pady=(0,6))
        flt.columnconfigure((0, 1, 2), weight=1)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._debounce(self._apply_filters))
        ctk.CTkEntry(flt, textvariable=self._search_var, placeholder_text="Search…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=30
                     ).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0,4))

        self._level_var = tk.StringVar(value="All Levels")
        ctk.CTkComboBox(flt, variable=self._level_var, values=["All Levels"] + LEVELS,
                        fg_color=SURFACE2, border_color=BORDER, button_color=ACCENT,
                        text_color=TEXT, dropdown_fg_color=SURFACE2, dropdown_text_color=TEXT,
                        height=28, font=ctk.CTkFont(size=12),
                        command=lambda _: self._apply_filters()
                        ).grid(row=1, column=0, sticky="ew", padx=(0,3))

        self._school_var = tk.StringVar(value="All Schools")
        ctk.CTkComboBox(flt, variable=self._school_var, values=["All Schools"] + SCHOOLS,
                        fg_color=SURFACE2, border_color=BORDER, button_color=ACCENT,
                        text_color=TEXT, dropdown_fg_color=SURFACE2, dropdown_text_color=TEXT,
                        height=28, font=ctk.CTkFont(size=12),
                        command=lambda _: self._apply_filters()
                        ).grid(row=1, column=1, sticky="ew", padx=3)

        self._class_var = tk.StringVar(value="All Classes")
        ctk.CTkComboBox(flt, variable=self._class_var, values=["All Classes"] + CLASSES,
                        fg_color=SURFACE2, border_color=BORDER, button_color=ACCENT,
                        text_color=TEXT, dropdown_fg_color=SURFACE2, dropdown_text_color=TEXT,
                        height=28, font=ctk.CTkFont(size=12),
                        command=lambda _: self._apply_filters()
                        ).grid(row=1, column=2, sticky="ew", padx=(3,0))

        self._list_frame = ScrollList(left, bg=SURFACE, accent=ACCENT)
        self._list_frame.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0,4))

        ctk.CTkButton(left, text="Export CSV", height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=self._export).grid(row=3, column=0, sticky="ew", padx=12, pady=(0,12))

        # ── Right panel ──────────────────────────────────────────────────────
        self._right = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        self._right.grid(row=0, column=1, sticky="nsew", padx=(8,16), pady=16)
        self._right.grid_columnconfigure(0, weight=1)
        self._right.grid_rowconfigure(1, weight=1)
        self._show_placeholder()

    # ── List ─────────────────────────────────────────────────────────────────

    RENDER_CAP = 200

    def _render_list(self):
        body = self._list_frame.body
        self._list_frame.clear()
        for s in self._spells[:self.RENDER_CAP]:
            color = SCHOOL_COLORS.get(s.get("school", ""), MUTED)
            lv = "C" if s.get("level", 0) == 0 else str(s["level"])
            row = tk.Frame(body, bg=SURFACE, cursor="hand2")
            row.pack(fill="x", padx=2, pady=1)
            tk.Label(row, text=lv, fg=ACCENT, bg=SURFACE, width=2,
                     font=("Segoe UI", 11, "bold")).pack(side="left", padx=(6, 2))
            tk.Label(row, text=s.get("school", ""), fg=color, bg=SURFACE,
                     font=("Segoe UI", 8)).pack(side="right", padx=6)
            tk.Label(row, text=s["name"], anchor="w", fg=TEXT, bg=SURFACE,
                     font=("Segoe UI", 11)).pack(side="left", fill="x", expand=True, pady=4)
            bind_row(row, lambda sp=s: self._select(sp), SURFACE, SURFACE2)
        if len(self._spells) > self.RENDER_CAP:
            tk.Label(body, text=f"Showing {self.RENDER_CAP} of {len(self._spells)} — "
                              f"narrow with Search or the filters.",
                     bg=SURFACE, fg=MUTED, font=("Segoe UI", 9), wraplength=240
                     ).pack(fill="x", padx=8, pady=8)
        self._list_frame.finalize()

    def refresh(self):
        self._apply_filters()

    def _apply_filters(self):
        lvl = self._level_var.get()
        level = "" if lvl == "All Levels" else (0 if lvl == "Cantrip" else int(lvl))
        school = self._school_var.get()
        cls = self._class_var.get()
        self._spells = self.db.list_spells(
            search=self._search_var.get().strip(),
            level=level,
            school="" if school == "All Schools" else school,
            cls="" if cls == "All Classes" else cls,
        )
        self._render_list()

    # ── Detail ─────────────────────────────────────────────────────────────────

    def _select(self, spell: dict):
        self._selected = spell
        self._show_detail(spell)

    def _show_placeholder(self):
        for w in self._right.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._right, text="Select a spell to view it",
                     text_color=MUTED, font=ctk.CTkFont(size=13)).pack(expand=True)

    def _show_detail(self, s: dict):
        for w in self._right.winfo_children():
            w.destroy()

        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text=s["name"], font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT, anchor="w").grid(row=0, column=0, sticky="ew")
        sub = f"{_lvl_label(s.get('level',0))} · {s.get('school','—')}"
        badges = []
        if s.get("ritual"): badges.append("ritual")
        if s.get("concentration"): badges.append("concentration")
        if badges: sub += "  (" + ", ".join(badges) + ")"
        ctk.CTkLabel(hdr, text=sub, text_color=SCHOOL_COLORS.get(s.get("school",""), MUTED),
                     font=ctk.CTkFont(size=12), anchor="w").grid(row=1, column=0, sticky="w")

        btn_row = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_row.grid(row=0, column=1, rowspan=2, sticky="ne")
        ctk.CTkButton(btn_row, text="Edit", width=64, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=lambda: self._show_edit(s)).pack(side="left", padx=(0,4))
        ctk.CTkButton(btn_row, text="Delete", width=64, height=28, fg_color=DANGER,
                      hover_color="#e74c3c", text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=lambda: self._delete(s)).pack(side="left")

        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        # Metadata grid
        meta = ctk.CTkFrame(self._right, fg_color="transparent")
        meta.pack(fill="x", padx=16, pady=(0,6))
        meta.columnconfigure(1, weight=1)
        r = 0
        for label, key in [("Casting Time","casting_time"), ("Range","range"),
                           ("Components","components"), ("Duration","duration"),
                           ("Classes","classes"), ("Source","source")]:
            val = s.get(key)
            if not val:
                continue
            ctk.CTkLabel(meta, text=label, text_color=MUTED, font=ctk.CTkFont(size=11),
                         width=110, anchor="w").grid(row=r, column=0, sticky="w", pady=1)
            ctk.CTkLabel(meta, text=str(val), text_color=TEXT, font=ctk.CTkFont(size=12),
                         anchor="w", justify="left", wraplength=420
                         ).grid(row=r, column=1, sticky="w", pady=1)
            r += 1

        md = MarkdownText(self._right, bg=SURFACE2)
        md.pack(fill="both", expand=True, padx=16, pady=(6,16))
        md.set_markdown(s.get("description", "") or "*(no description)*")

    # ── Edit / create ──────────────────────────────────────────────────────────

    def _new(self):
        self._show_edit({})

    def _show_edit(self, s: dict):
        for w in self._right.winfo_children():
            w.destroy()
        is_new = not s.get("id")

        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        ctk.CTkLabel(hdr, text="New Spell" if is_new else f"Edit: {s.get('name','')}",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT, anchor="w"
                     ).pack(side="left")
        form: dict = {}
        ctk.CTkButton(hdr, text="Cancel", width=72, height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=lambda: (self._show_detail(s) if not is_new else self._show_placeholder())
                      ).pack(side="right")
        ctk.CTkButton(hdr, text="Save", width=72, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=lambda: self._save(s.get("id"), form)).pack(side="right", padx=(0,6))

        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        body = ctk.CTkScrollableFrame(self._right, fg_color="transparent",
                                      scrollbar_button_color=ACCENT)
        body.pack(fill="both", expand=True, padx=8, pady=(0,8))
        body.columnconfigure(1, weight=1)

        def field_row(row, label):
            ctk.CTkLabel(body, text=label, text_color=MUTED, font=ctk.CTkFont(size=12),
                         width=110, anchor="e").grid(row=row, column=0, sticky="e",
                                                     padx=(8,4), pady=3)

        def entry(row, key, default=""):
            field_row(row, key.replace("_", " ").title())
            var = tk.StringVar(value=str(s.get(key, default) or default))
            ctk.CTkEntry(body, textvariable=var, fg_color=SURFACE2, border_color=BORDER,
                         text_color=TEXT, height=28).grid(row=row, column=1, sticky="ew", pady=3)
            form[key] = var

        r = 0
        entry(r, "name"); r += 1

        field_row(r, "Level")
        lvl_var = tk.StringVar(value=("Cantrip" if s.get("level", 0) == 0 else str(s.get("level", 1))))
        ctk.CTkOptionMenu(body, variable=lvl_var, values=LEVELS, fg_color=SURFACE2,
                          button_color=ACCENT, button_hover_color=ACCENT_H, text_color=TEXT
                          ).grid(row=r, column=1, sticky="w", pady=3); form["level"] = lvl_var; r += 1

        field_row(r, "School")
        school_var = tk.StringVar(value=s.get("school", "Evocation") or "Evocation")
        ctk.CTkOptionMenu(body, variable=school_var, values=SCHOOLS, fg_color=SURFACE2,
                          button_color=ACCENT, button_hover_color=ACCENT_H, text_color=TEXT
                          ).grid(row=r, column=1, sticky="w", pady=3); form["school"] = school_var; r += 1

        entry(r, "casting_time", "1 action"); r += 1
        entry(r, "range"); r += 1
        entry(r, "components", "V, S"); r += 1
        entry(r, "duration", "Instantaneous"); r += 1
        entry(r, "classes"); r += 1
        entry(r, "source"); r += 1

        flags = ctk.CTkFrame(body, fg_color="transparent")
        flags.grid(row=r, column=1, sticky="w", pady=3)
        conc_var = tk.BooleanVar(value=bool(s.get("concentration")))
        rit_var = tk.BooleanVar(value=bool(s.get("ritual")))
        ctk.CTkCheckBox(flags, text="Concentration", variable=conc_var, text_color=TEXT,
                        fg_color=ACCENT, hover_color=ACCENT_H, border_color=BORDER,
                        checkbox_width=18, checkbox_height=18).pack(side="left", padx=(0,12))
        ctk.CTkCheckBox(flags, text="Ritual", variable=rit_var, text_color=TEXT,
                        fg_color=ACCENT, hover_color=ACCENT_H, border_color=BORDER,
                        checkbox_width=18, checkbox_height=18).pack(side="left")
        form["concentration"] = conc_var; form["ritual"] = rit_var; r += 1

        field_row(r, "Description")
        desc = ctk.CTkTextbox(body, height=160, fg_color=SURFACE2, border_color=BORDER,
                              text_color=TEXT, font=ctk.CTkFont(size=12), wrap="word")
        desc.insert("1.0", s.get("description", ""))
        desc.grid(row=r, column=1, sticky="ew", pady=3); form["description"] = desc; r += 1
        body.rowconfigure(r-1, weight=1)

    def _save(self, id, form: dict):
        name = form["name"].get().strip()
        if not name:
            messagebox.showerror("Validation", "Name is required."); return
        lvl_str = form["level"].get()
        level = 0 if lvl_str == "Cantrip" else int(lvl_str)
        data = {
            "name": name, "level": level, "school": form["school"].get(),
            "casting_time": form["casting_time"].get().strip(),
            "range": form["range"].get().strip(),
            "components": form["components"].get().strip(),
            "duration": form["duration"].get().strip(),
            "concentration": form["concentration"].get(),
            "ritual": form["ritual"].get(),
            "classes": form["classes"].get().strip(),
            "source": form["source"].get().strip() or None,
            "description": form["description"].get("1.0", "end").rstrip(),
        }
        if id:
            self.db.update_spell(id, data)
        else:
            id = self.db.create_spell(data)
        self.refresh()
        saved = next((sp for sp in self._spells if sp["id"] == id), None)
        if saved:
            self._show_detail(saved)

    def _delete(self, s: dict):
        if messagebox.askyesno("Delete", f"Delete '{s['name']}'?"):
            self.db.delete_spell(s["id"])
            self._selected = None
            self.refresh()
            self._show_placeholder()

    def _clear_all(self):
        n = len(self._spells)
        if n == 0:
            messagebox.showinfo("Clear All", "No spells to clear."); return
        if messagebox.askyesno("Clear All Spells",
                               f"Permanently delete all {n} spell(s)? This cannot be undone."):
            self.db.clear_table("spells")
            self._selected = None
            self.refresh()
            self._show_placeholder()

    def _export(self):
        path = filedialog.asksaveasfilename(
            title="Export Spells CSV", defaultextension=".csv",
            filetypes=[("CSV","*.csv")], initialfile="spells.csv")
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write(self.db.export_csv("spells"))
            messagebox.showinfo("Export", f"Exported to:\n{path}")
