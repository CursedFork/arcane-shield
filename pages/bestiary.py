"""Bestiary page."""
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


class BestiaryPage(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._entries: list[dict] = []
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

        # ── Left panel ─────────────────────────────────────────────────────────
        left = ctk.CTkFrame(self, width=300, fg_color=SURFACE, corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(16,8), pady=16)
        left.grid_propagate(False)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,6))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="Bestiary", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="+ New", width=64, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._new_entry).grid(row=0, column=1, sticky="e")
        ctk.CTkButton(hdr, text="Clear All", width=72, height=28,
                      fg_color="transparent", hover_color=DANGER, text_color=MUTED,
                      font=ctk.CTkFont(size=12),
                      command=self._clear_all).grid(row=0, column=2, sticky="e", padx=(4,0))

        flt = ctk.CTkFrame(left, fg_color="transparent")
        flt.grid(row=1, column=0, sticky="ew", padx=12, pady=(0,6))
        flt.columnconfigure((0, 1), weight=1)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._debounce(self._apply_filters))
        ctk.CTkEntry(flt, textvariable=self._search_var, placeholder_text="Search…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT,
                     height=30).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0,4))

        self._cr_var = tk.StringVar(value="All CR")
        self._cr_cb = ctk.CTkComboBox(flt, variable=self._cr_var, values=["All CR"],
                                       fg_color=SURFACE2, border_color=BORDER,
                                       button_color=ACCENT, text_color=TEXT,
                                       dropdown_fg_color=SURFACE2, dropdown_text_color=TEXT,
                                       height=28, font=ctk.CTkFont(size=12),
                                       command=lambda _: self._apply_filters())
        self._cr_cb.grid(row=1, column=0, sticky="ew", padx=(0,3))

        self._type_var = tk.StringVar(value="All Types")
        self._type_cb = ctk.CTkComboBox(flt, variable=self._type_var, values=["All Types"],
                                        fg_color=SURFACE2, border_color=BORDER,
                                        button_color=ACCENT, text_color=TEXT,
                                        dropdown_fg_color=SURFACE2, dropdown_text_color=TEXT,
                                        height=28, font=ctk.CTkFont(size=12),
                                        command=lambda _: self._apply_filters())
        self._type_cb.grid(row=1, column=1, sticky="ew", padx=(3,0))

        self._list_frame = ScrollList(left, bg=SURFACE, accent=ACCENT)
        self._list_frame.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0,4))

        ctk.CTkButton(left, text="Export CSV", height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=self._export).grid(row=3, column=0, sticky="ew", padx=12, pady=(0,12))

        # ── Right panel ────────────────────────────────────────────────────────
        self._right = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        self._right.grid(row=0, column=1, sticky="nsew", padx=(8,16), pady=16)
        self._right.grid_columnconfigure(0, weight=1)
        self._right.grid_rowconfigure(1, weight=1)
        self._show_placeholder()

    RENDER_CAP = 150

    def _render_list(self, entries: list[dict]):
        # Plain tk rows in a ScrollList, kept to 2 widgets each — list rebuilds
        # (filtering/searching) feel instant even with thousands of records.
        body = self._list_frame.body
        self._list_frame.clear()
        for e in entries[:self.RENDER_CAP]:
            row = tk.Frame(body, bg=SURFACE, cursor="hand2")
            row.pack(fill="x", padx=2, pady=1)
            tk.Label(row, text=f"CR {e.get('cr','?')} · AC {e.get('ac','?')} · {e.get('max_hp','?')}HP",
                     anchor="e", bg=SURFACE, fg=MUTED, font=("Segoe UI", 8)
                     ).pack(side="right", padx=8)
            tk.Label(row, text=e["name"], anchor="w", bg=SURFACE, fg=TEXT,
                     font=("Segoe UI", 11)).pack(side="left", fill="x", expand=True,
                                                 padx=8, pady=4)
            bind_row(row, lambda en=e: self._select(en), SURFACE, SURFACE2)
        if len(entries) > self.RENDER_CAP:
            tk.Label(body,
                     text=f"Showing {self.RENDER_CAP} of {len(entries)} — "
                          f"narrow with Search or the filters.",
                     bg=SURFACE, fg=MUTED, font=("Segoe UI", 9), wraplength=240
                     ).pack(fill="x", padx=8, pady=8)
        self._list_frame.finalize()

    def _apply_filters(self):
        search = self._search_var.get().strip()
        cr = self._cr_var.get()
        mtype = self._type_var.get()
        entries = self.db.list_bestiary(
            search=search,
            cr="" if cr == "All CR" else cr,
            tag="" if mtype == "All Types" else mtype,
        )
        self._entries = entries
        self._render_list(entries)

    def refresh(self):
        crs = self.db.bestiary_crs()
        self._cr_cb.configure(values=["All CR"] + crs)
        self._type_cb.configure(values=["All Types"] + self.db.bestiary_types())
        self._apply_filters()

    def _select(self, entry: dict):
        self._selected = entry
        self._show_detail(entry)

    def _show_placeholder(self):
        for w in self._right.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._right, text="Select an entry to view its statblock",
                     text_color=MUTED, font=ctk.CTkFont(size=13)).pack(expand=True)

    def _show_detail(self, entry: dict):
        for w in self._right.winfo_children():
            w.destroy()

        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        hdr.columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr, text=entry["name"],
                     font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT,
                     anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(hdr, text=f"CR {entry.get('cr','?')} · AC {entry.get('ac','?')} · {entry.get('max_hp','?')} HP · Init +{entry.get('initiative_mod',0)}",
                     text_color=MUTED, font=ctk.CTkFont(size=12), anchor="w"
                     ).grid(row=1, column=0, sticky="w")

        btn_row = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_row.grid(row=0, column=1, rowspan=2, sticky="ne")
        ctk.CTkButton(btn_row, text="Edit", width=64, height=28,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=TEXT,
                      font=ctk.CTkFont(size=12),
                      command=lambda: self._show_edit(entry)).pack(side="left", padx=(0,4))
        ctk.CTkButton(btn_row, text="Delete", width=64, height=28,
                      fg_color=DANGER, hover_color="#e74c3c", text_color=TEXT,
                      font=ctk.CTkFont(size=12),
                      command=lambda: self._delete(entry)).pack(side="left")

        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        if entry.get("tags"):
            ctk.CTkLabel(self._right, text="Tags: " + ", ".join(entry["tags"]),
                         text_color=MUTED, font=ctk.CTkFont(size=11), anchor="w"
                         ).pack(fill="x", padx=16, pady=(0,8))

        # Statblock rendered as Markdown
        md = MarkdownText(self._right, bg=SURFACE2)
        md.pack(fill="both", expand=True, padx=16, pady=(0,16))
        md.set_markdown(entry.get("statblock_md", "*(no statblock)*"))

    def _new_entry(self):
        self._show_edit({})

    def _show_edit(self, entry: dict):
        for w in self._right.winfo_children():
            w.destroy()

        is_new = not entry.get("id")
        title = "New Entry" if is_new else f"Edit: {entry.get('name','')}"

        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        ctk.CTkLabel(hdr, text=title, font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=TEXT, anchor="w").pack(side="left")
        form = {}
        ctk.CTkButton(hdr, text="Cancel", width=72, height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=lambda: (self._show_detail(entry) if not is_new else self._show_placeholder())
                      ).pack(side="right")
        ctk.CTkButton(hdr, text="Save", width=72, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=lambda: self._save(entry.get("id"), form)
                      ).pack(side="right", padx=(0,6))

        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        scroll = ctk.CTkScrollableFrame(self._right, fg_color="transparent",
                                         scrollbar_button_color=ACCENT)
        scroll.pack(fill="both", expand=True, padx=8, pady=(0,8))
        scroll.columnconfigure(1, weight=1)

        def lbl_entry(label, key, row, default="", placeholder=""):
            ctk.CTkLabel(scroll, text=label, text_color=MUTED, font=ctk.CTkFont(size=12),
                         width=130, anchor="e").grid(row=row, column=0, sticky="e", padx=(8,6), pady=4)
            var = tk.StringVar(value=str(entry.get(key, default)))
            ctk.CTkEntry(scroll, textvariable=var, fg_color=SURFACE2, border_color=BORDER,
                         text_color=TEXT, placeholder_text=placeholder, height=30
                         ).grid(row=row, column=1, sticky="ew", padx=(0,8), pady=4)
            form[key] = var
            return var

        r = 0
        lbl_entry("Name *", "name", r, placeholder="Goblin, Dragon…"); r+=1
        lbl_entry("CR", "cr", r, "0", "0, 1/4, 1, 5…"); r+=1
        lbl_entry("AC", "ac", r, "10"); r+=1
        lbl_entry("Max HP", "max_hp", r, "1"); r+=1
        lbl_entry("Initiative Mod", "initiative_mod", r, "0"); r+=1
        lbl_entry("Tags", "tags", r, placeholder="Undead;Fire;Boss"); r+=1
        if isinstance(entry.get("tags"), list):
            form["tags"].set(";".join(entry["tags"]))

        ctk.CTkLabel(scroll, text="Statblock", text_color=MUTED,
                     font=ctk.CTkFont(size=12), anchor="ne", width=130
                     ).grid(row=r, column=0, sticky="ne", padx=(8,6), pady=4)
        tb = ctk.CTkTextbox(scroll, height=300, fg_color=SURFACE2, border_color=BORDER,
                             text_color=TEXT, font=ctk.CTkFont(family="Courier New", size=12),
                             wrap="word")
        tb.insert("1.0", entry.get("statblock_md",""))
        tb.grid(row=r, column=1, sticky="ew", padx=(0,8), pady=4)
        form["statblock_md"] = tb

    def _save(self, id, form: dict):
        name = form["name"].get().strip()
        if not name:
            messagebox.showerror("Validation", "Name is required."); return

        def gv(key):
            v = form.get(key)
            if v is None: return ""
            if isinstance(v, ctk.CTkTextbox): return v.get("1.0","end").rstrip()
            return v.get().strip()

        tags_raw = gv("tags")
        tags = [t.strip() for t in tags_raw.replace(";",",").split(",") if t.strip()]

        data = {
            "name": name, "cr": gv("cr") or "0",
            "ac": gv("ac") or "10", "max_hp": gv("max_hp") or "1",
            "initiative_mod": gv("initiative_mod") or "0",
            "statblock_md": gv("statblock_md"), "tags": tags,
        }

        if id:
            self.db.update_bestiary_entry(id, data)
        else:
            id = self.db.create_bestiary_entry(data)

        self.refresh()
        saved = next((e for e in self._entries if e["id"] == id), None)
        if saved:
            self._show_detail(saved)

    def _delete(self, entry: dict):
        if messagebox.askyesno("Delete", f"Delete '{entry['name']}'?"):
            self.db.delete_bestiary_entry(entry["id"])
            self._selected = None
            self.refresh()
            self._show_placeholder()

    def _clear_all(self):
        n = len(self._items)
        if n == 0:
            messagebox.showinfo("Clear All", "No bestiary entries to clear.")
            return
        if messagebox.askyesno("Clear All Bestiary",
                               f"Permanently delete all {n} entr(ies)? This cannot be undone."):
            self.db.clear_table("bestiary")
            self._selected = None
            self.refresh()
            self._show_placeholder()

    def _export(self):
        path = filedialog.asksaveasfilename(
            title="Export Bestiary CSV", defaultextension=".csv",
            filetypes=[("CSV files","*.csv")], initialfile="bestiary.csv"
        )
        if path:
            with open(path,"w",newline="",encoding="utf-8") as f:
                f.write(self.db.export_csv("bestiary"))
            messagebox.showinfo("Export", f"Exported to:\n{path}")
