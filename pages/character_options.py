"""Character Options page — sub-tabs for Races, Classes, Subclasses,
Backgrounds and Feats (the build-a-character reference material)."""
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

# (category key, sub-tab label, parent-field label / "" to hide)
CATEGORIES = [
    ("race",       "🧝  Races",       "Subrace of"),
    ("class",      "🛡  Classes",      ""),
    ("subclass",   "📜  Subclasses",  "Class"),
    ("background", "🎭  Backgrounds", ""),
    ("feat",       "⭐  Feats",        ""),
]


class CharacterOptionsPage(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(self, fg_color=SURFACE, height=42, corner_radius=8)
        bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16,4))

        self._tab_btns: list[ctk.CTkButton] = []
        self._tabs: list[_CategoryTab] = []
        self._active = 0

        for i, (cat, label, parent_label) in enumerate(CATEGORIES):
            btn = ctk.CTkButton(bar, text=label, height=34, fg_color="transparent",
                                hover_color=SURFACE2, text_color=MUTED,
                                font=ctk.CTkFont(size=13), corner_radius=6,
                                command=lambda i=i: self._switch(i))
            btn.pack(side="left", padx=(4,0), pady=4)
            self._tab_btns.append(btn)
            tab = _CategoryTab(self, self.db, cat, label, parent_label)
            tab.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0,16))
            tab.grid_remove()
            self._tabs.append(tab)

        self._switch(0)

    def _switch(self, i: int):
        for j, (btn, tab) in enumerate(zip(self._tab_btns, self._tabs)):
            if j == i:
                btn.configure(fg_color=ACCENT, text_color=TEXT)
                tab.grid(); tab.refresh()
            else:
                btn.configure(fg_color="transparent", text_color=MUTED)
                tab.grid_remove()
        self._active = i

    def refresh(self):
        self._tabs[self._active].refresh()


class _CategoryTab(ctk.CTkFrame):
    def __init__(self, parent, db, category, label, parent_label):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self.category = category
        self.label = label.split("  ")[-1]   # plain name, e.g. "Races"
        self.parent_label = parent_label
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

        left = ctk.CTkFrame(self, width=280, fg_color=SURFACE, corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,8), pady=0)
        left.grid_propagate(False)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,6))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text=self.label, font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="+ New", width=60, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._new).grid(row=0, column=1, sticky="e")
        ctk.CTkButton(hdr, text="Clear", width=58, height=28, fg_color="transparent",
                      hover_color=DANGER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=self._clear).grid(row=0, column=2, sticky="e", padx=(4,0))

        srow = ctk.CTkFrame(left, fg_color="transparent")
        srow.grid(row=1, column=0, sticky="ew", padx=12, pady=(0,6))
        srow.columnconfigure(0, weight=1)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._debounce(self._apply))
        ctk.CTkEntry(srow, textvariable=self._search_var, placeholder_text="Search…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=30
                     ).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(srow, text="⟲", width=30, height=30, fg_color="transparent",
                      hover_color=SURFACE2, text_color=MUTED, font=ctk.CTkFont(size=13),
                      command=self._reset_filters).grid(row=0, column=1, padx=(4,0))

        # Feat-only filters: source (XPHB = newer rules), boon, prerequisite.
        if self.category == "feat":
            cb_kw = dict(fg_color=SURFACE2, border_color=BORDER, button_color=ACCENT,
                         text_color=TEXT, dropdown_fg_color=SURFACE2, dropdown_text_color=TEXT,
                         height=26, font=ctk.CTkFont(size=11))
            self._feat_source_var = tk.StringVar(value="All Sources")
            self._feat_source_cb = ctk.CTkComboBox(srow, variable=self._feat_source_var,
                                                   values=["All Sources"],
                                                   command=lambda _: self._apply(), **cb_kw)
            self._feat_source_cb.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4,0))
            self._feat_boon_var = tk.StringVar(value="All feats")
            ctk.CTkComboBox(srow, variable=self._feat_boon_var,
                            values=["All feats", "Boons only", "Exclude boons"],
                            command=lambda _: self._apply(), **cb_kw
                            ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4,0))
            self._feat_prereq_var = tk.StringVar(value="Any prerequisite")
            ctk.CTkComboBox(srow, variable=self._feat_prereq_var,
                            values=["Any prerequisite", "Has prerequisite", "No prerequisite"],
                            command=lambda _: self._apply(), **cb_kw
                            ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4,0))

        self._list_frame = ScrollList(left, bg=SURFACE, accent=ACCENT)
        self._list_frame.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0,4))

        ctk.CTkButton(left, text="Export CSV", height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=self._export).grid(row=3, column=0, sticky="ew", padx=12, pady=(0,12))

        self._right = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        self._right.grid(row=0, column=1, sticky="nsew", padx=(8,0), pady=0)
        self._right.grid_columnconfigure(0, weight=1)
        self._right.grid_rowconfigure(1, weight=1)
        self._show_placeholder()

    def _render_list(self):
        body = self._list_frame.body
        self._list_frame.clear()
        for it in self._items:
            row = tk.Frame(body, bg=SURFACE, cursor="hand2")
            row.pack(fill="x", padx=2, pady=1)
            if it.get("parent"):
                tk.Label(row, text=it["parent"], anchor="e", bg=SURFACE, fg=MUTED,
                         font=("Segoe UI", 8)).pack(side="right", padx=8)
            tk.Label(row, text=it["name"], anchor="w", bg=SURFACE, fg=TEXT,
                     font=("Segoe UI", 11)).pack(side="left", fill="x", expand=True,
                                                 padx=8, pady=6)
            bind_row(row, lambda x=it: self._show_detail(x), SURFACE, SURFACE2)
        self._list_frame.finalize()

    def _reset_filters(self):
        self._search_var.set("")
        if self.category == "feat":
            self._feat_source_var.set("All Sources")
            self._feat_boon_var.set("All feats")
            self._feat_prereq_var.set("Any prerequisite")
        self._apply()

    def refresh(self):
        if self.category == "feat":
            self._feat_source_cb.configure(values=["All Sources"] + self.db.char_feat_sources())
        self._apply()

    def _apply(self):
        kw = dict(category=self.category, search=self._search_var.get().strip())
        if self.category == "feat":
            src = self._feat_source_var.get()
            kw["source"] = "" if src == "All Sources" else src
            b = self._feat_boon_var.get()
            kw["boon"] = True if b == "Boons only" else (False if b == "Exclude boons" else None)
            pr = self._feat_prereq_var.get()
            kw["prereq"] = True if pr == "Has prerequisite" else (False if pr == "No prerequisite" else None)
        self._items = self.db.list_char_options(**kw)
        self._render_list()

    def _show_placeholder(self):
        for w in self._right.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._right, text=f"Select a {self.label[:-1].lower()} to view it",
                     text_color=MUTED, font=ctk.CTkFont(size=13)).pack(expand=True)

    def _show_detail(self, it: dict):
        for w in self._right.winfo_children():
            w.destroy()
        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text=it["name"], font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT, anchor="w").grid(row=0, column=0, sticky="ew")
        sub = []
        if it.get("parent"):
            sub.append(f"{self.parent_label or 'Parent'}: {it['parent']}")
        if it.get("source"):
            sub.append(it["source"])
        if sub:
            ctk.CTkLabel(hdr, text="  ·  ".join(sub), text_color=MUTED,
                         font=ctk.CTkFont(size=12), anchor="w").grid(row=1, column=0, sticky="w")

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
        md.pack(fill="both", expand=True, padx=16, pady=(0,16))
        md.set_markdown(it.get("body_md", "") or "*(no details)*")

    def _new(self):
        self._show_edit({})

    def _show_edit(self, it: dict):
        for w in self._right.winfo_children():
            w.destroy()
        is_new = not it.get("id")
        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        ctk.CTkLabel(hdr, text=("New " + self.label[:-1]) if is_new else f"Edit: {it.get('name','')}",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT, anchor="w"
                     ).pack(side="left")
        ctk.CTkButton(hdr, text="Cancel", width=72, height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=lambda: (self._show_detail(it) if not is_new else self._show_placeholder())
                      ).pack(side="right")

        name_var = tk.StringVar(value=it.get("name", ""))
        parent_var = tk.StringVar(value=it.get("parent", ""))
        source_var = tk.StringVar(value=it.get("source", "") or "")

        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Validation", "Name is required."); return
            data = {
                "category": self.category, "name": name,
                "parent": parent_var.get().strip(),
                "source": source_var.get().strip() or None,
                "body_md": body.get("1.0", "end").rstrip(),
            }
            if it.get("id"):
                self.db.update_char_option(it["id"], data)
            else:
                self.db.create_char_option(data)
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

        def labeled(row, text, var, placeholder=""):
            ctk.CTkLabel(form, text=text, text_color=MUTED, font=ctk.CTkFont(size=12),
                         width=90, anchor="e").grid(row=row, column=0, sticky="e", padx=(8,4), pady=3)
            ctk.CTkEntry(form, textvariable=var, fg_color=SURFACE2, border_color=BORDER,
                         text_color=TEXT, height=28, placeholder_text=placeholder
                         ).grid(row=row, column=1, sticky="ew", pady=3)

        r = 0
        labeled(r, "Name", name_var); r += 1
        if self.parent_label:
            labeled(r, self.parent_label, parent_var, "optional"); r += 1
        labeled(r, "Source", source_var, "optional"); r += 1

        ctk.CTkLabel(form, text="Details", text_color=MUTED, font=ctk.CTkFont(size=12),
                     anchor="ne").grid(row=r, column=0, sticky="ne", padx=(8,4), pady=3)
        body = ctk.CTkTextbox(form, fg_color=SURFACE2, border_color=BORDER, text_color=TEXT,
                              font=ctk.CTkFont(size=13), wrap="word")
        body.insert("1.0", it.get("body_md", ""))
        body.grid(row=r, column=1, sticky="nsew", pady=3)
        form.rowconfigure(r, weight=1)

    def _delete(self, it: dict):
        if messagebox.askyesno("Delete", f"Delete '{it['name']}'?"):
            self.db.delete_char_option(it["id"])
            self.refresh()
            self._show_placeholder()

    def _clear(self):
        # Count the whole category (not the search-filtered view).
        n = len(self.db.list_char_options(category=self.category))
        if n == 0:
            messagebox.showinfo("Clear", f"No {self.label.lower()} to clear."); return
        if messagebox.askyesno(f"Clear {self.label}",
                               f"Delete ALL {n} {self.label.lower()}? This cannot be undone."):
            self.db.clear_char_category(self.category)
            self.refresh()
            self._show_placeholder()

    def _export(self):
        path = filedialog.asksaveasfilename(
            title=f"Export {self.label} CSV", defaultextension=".csv",
            filetypes=[("CSV","*.csv")], initialfile="character_options.csv")
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write(self.db.export_csv("character_options"))
            messagebox.showinfo("Export", f"Exported to:\n{path}")
