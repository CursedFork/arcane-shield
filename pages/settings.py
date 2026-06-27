"""Setting Information page — lore for published settings (Eberron, Ravnica…)."""
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


class SettingsPage(ctk.CTkFrame):
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

        left = ctk.CTkFrame(self, width=280, fg_color=SURFACE, corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(16,8), pady=16)
        left.grid_propagate(False)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,6))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="Settings", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="+ New", width=60, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._new).grid(row=0, column=1, sticky="e")
        ctk.CTkButton(hdr, text="Clear", width=58, height=28, fg_color="transparent",
                      hover_color=DANGER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=self._clear).grid(row=0, column=2, sticky="e", padx=(4,0))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._debounce(self._apply))
        ctk.CTkEntry(left, textvariable=self._search_var, placeholder_text="Search…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=30
                     ).grid(row=1, column=0, sticky="ew", padx=12, pady=(0,6))

        self._list_frame = ScrollList(left, bg=SURFACE, accent=ACCENT)
        self._list_frame.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0,4))

        ctk.CTkButton(left, text="Export CSV", height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=self._export).grid(row=3, column=0, sticky="ew", padx=12, pady=(0,12))

        self._right = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        self._right.grid(row=0, column=1, sticky="nsew", padx=(8,16), pady=16)
        self._right.grid_columnconfigure(0, weight=1)
        self._right.grid_rowconfigure(1, weight=1)
        self._show_placeholder()

    def _render_list(self):
        body = self._list_frame.body
        self._list_frame.clear()
        for it in self._items:
            row = tk.Frame(body, bg=SURFACE, cursor="hand2")
            row.pack(fill="x", padx=2, pady=1)
            tk.Label(row, text=it["name"], anchor="w", fg=TEXT, bg=SURFACE,
                     font=("Segoe UI", 11)).pack(side="left", fill="x", expand=True,
                                                 padx=8, pady=6)
            bind_row(row, lambda x=it: self._show_detail(x), SURFACE, SURFACE2)
        self._list_frame.finalize()

    def refresh(self):
        self._apply()

    def _apply(self):
        self._items = self.db.list_settings(search=self._search_var.get().strip())
        self._render_list()

    def _show_placeholder(self):
        for w in self._right.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._right, text="Select a setting to view its lore",
                     text_color=MUTED, font=ctk.CTkFont(size=13)).pack(expand=True)

    def _show_detail(self, it: dict):
        for w in self._right.winfo_children():
            w.destroy()
        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text=it["name"], font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT, anchor="w").grid(row=0, column=0, sticky="ew")
        btns = ctk.CTkFrame(hdr, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="ne")
        ctk.CTkButton(btns, text="Edit", width=64, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=lambda: self._show_edit(it)).pack(side="left", padx=(0,4))
        ctk.CTkButton(btns, text="Delete", width=64, height=28, fg_color=DANGER,
                      hover_color="#e74c3c", text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=lambda: self._delete(it)).pack(side="left")
        if it.get("tags"):
            ctk.CTkLabel(self._right, text="Tags: " + ", ".join(it["tags"]),
                         text_color=MUTED, font=ctk.CTkFont(size=11), anchor="w"
                         ).pack(fill="x", padx=16, pady=(0,4))
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
        ctk.CTkLabel(hdr, text="New Setting" if is_new else f"Edit: {it.get('name','')}",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT, anchor="w"
                     ).pack(side="left")
        ctk.CTkButton(hdr, text="Cancel", width=72, height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=lambda: (self._show_detail(it) if not is_new else self._show_placeholder())
                      ).pack(side="right")

        name_var = tk.StringVar(value=it.get("name", ""))
        tags_var = tk.StringVar(value=";".join(it.get("tags", []) if isinstance(it.get("tags"), list) else []))

        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Validation", "Name is required."); return
            tags = [t.strip() for t in tags_var.get().replace(";", ",").split(",") if t.strip()]
            data = {"name": name, "body_md": body.get("1.0", "end").rstrip(), "tags": tags}
            if it.get("id"):
                self.db.update_setting(it["id"], data)
            else:
                self.db.create_setting(data)
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
                     width=70, anchor="e").grid(row=0, column=0, sticky="e", padx=(8,4), pady=3)
        ctk.CTkEntry(form, textvariable=name_var, fg_color=SURFACE2, border_color=BORDER,
                     text_color=TEXT, height=28).grid(row=0, column=1, sticky="ew", pady=3)
        ctk.CTkLabel(form, text="Tags", text_color=MUTED, font=ctk.CTkFont(size=12),
                     width=70, anchor="e").grid(row=1, column=0, sticky="e", padx=(8,4), pady=3)
        ctk.CTkEntry(form, textvariable=tags_var, fg_color=SURFACE2, border_color=BORDER,
                     text_color=TEXT, height=28, placeholder_text="Tag1;Tag2"
                     ).grid(row=1, column=1, sticky="ew", pady=3)
        ctk.CTkLabel(form, text="Lore", text_color=MUTED, font=ctk.CTkFont(size=12),
                     width=70, anchor="ne").grid(row=2, column=0, sticky="ne", padx=(8,4), pady=3)
        body = ctk.CTkTextbox(form, fg_color=SURFACE2, border_color=BORDER, text_color=TEXT,
                              font=ctk.CTkFont(size=13), wrap="word")
        body.insert("1.0", it.get("body_md", ""))
        body.grid(row=2, column=1, sticky="nsew", pady=3)
        form.rowconfigure(2, weight=1)

    def _delete(self, it: dict):
        if messagebox.askyesno("Delete", f"Delete '{it['name']}'?"):
            self.db.delete_setting(it["id"])
            self.refresh()
            self._show_placeholder()

    def _clear(self):
        n = len(self.db.list_settings())  # whole table, not the filtered view
        if n == 0:
            messagebox.showinfo("Clear", "Nothing to clear."); return
        if messagebox.askyesno("Clear All", f"Delete ALL {n} setting entries (the entire table)?"):
            self.db.clear_table("settings_lore")
            self.refresh()
            self._show_placeholder()

    def _export(self):
        path = filedialog.asksaveasfilename(
            title="Export Settings CSV", defaultextension=".csv",
            filetypes=[("CSV","*.csv")], initialfile="settings.csv")
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write(self.db.export_csv("settings_lore"))
            messagebox.showinfo("Export", f"Exported to:\n{path}")
