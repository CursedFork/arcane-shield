"""Mechanics page."""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from pages.md_widget import MarkdownText

BG       = "#0f0f13"
SURFACE  = "#1a1a24"
SURFACE2 = "#22222f"
BORDER   = "#2e2e3e"
ACCENT   = "#7c5cbf"
ACCENT_H = "#9472d8"
TEXT     = "#e2e0f0"
MUTED    = "#8a8aa0"
DANGER   = "#c0392b"


class MechanicsPage(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._items: list[dict] = []
        self._build()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left
        left = ctk.CTkFrame(self, width=280, fg_color=SURFACE, corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(16,8), pady=16)
        left.grid_propagate(False)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,6))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="Mechanics", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="+ New", width=64, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._new).grid(row=0, column=1, sticky="e")
        ctk.CTkButton(hdr, text="Clear All", width=72, height=28,
                      fg_color="transparent", hover_color=DANGER, text_color=MUTED,
                      font=ctk.CTkFont(size=12),
                      command=self._clear_all).grid(row=0, column=2, sticky="e", padx=(4,0))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self.refresh())
        ctk.CTkEntry(left, textvariable=self._search_var, placeholder_text="Search…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=30
                     ).grid(row=1, column=0, sticky="ew", padx=12, pady=(0,6))

        self._list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent",
                                                   scrollbar_button_color=ACCENT)
        self._list_frame.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0,4))
        self._list_frame.columnconfigure(0, weight=1)

        ctk.CTkButton(left, text="Export CSV", height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=self._export).grid(row=3, column=0, sticky="ew", padx=12, pady=(0,12))

        # Right
        self._right = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        self._right.grid(row=0, column=1, sticky="nsew", padx=(8,16), pady=16)
        self._right.grid_columnconfigure(0, weight=1)
        self._right.grid_rowconfigure(1, weight=1)
        self._show_placeholder()

    def _render_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()
        for item in self._items:
            row = ctk.CTkFrame(self._list_frame, fg_color="transparent", cursor="hand2")
            row.pack(fill="x", padx=2, pady=1)
            row.columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=item["title"], anchor="w", text_color=TEXT,
                         font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="ew", padx=8, pady=5)
            if item.get("campaign"):
                ctk.CTkLabel(row, text=item["campaign"], anchor="e", text_color=MUTED,
                             font=ctk.CTkFont(size=11)).grid(row=0, column=1, padx=(0,8))
            row.bind("<Button-1>", lambda e, it=item: self._select(it))
            for c in row.winfo_children():
                c.bind("<Button-1>", lambda e, it=item: self._select(it))

    def refresh(self):
        self._items = self.db.list_mechanics(search=self._search_var.get().strip())
        self._render_list()

    def _select(self, item: dict):
        self._show_detail(item)

    def _show_placeholder(self):
        for w in self._right.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._right, text="Select a mechanic to view it",
                     text_color=MUTED, font=ctk.CTkFont(size=13)).pack(expand=True)

    def _show_detail(self, item: dict):
        for w in self._right.winfo_children():
            w.destroy()

        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text=item["title"],
                     font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT, anchor="w"
                     ).grid(row=0, column=0, sticky="ew")
        if item.get("campaign"):
            ctk.CTkLabel(hdr, text=item["campaign"], text_color=MUTED,
                         font=ctk.CTkFont(size=12), anchor="w").grid(row=1, column=0, sticky="w")

        btn_row = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_row.grid(row=0, column=1, rowspan=2, sticky="ne")
        ctk.CTkButton(btn_row, text="Edit", width=64, height=28,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=TEXT,
                      font=ctk.CTkFont(size=12),
                      command=lambda: self._show_edit(item)).pack(side="left", padx=(0,4))
        ctk.CTkButton(btn_row, text="Delete", width=64, height=28,
                      fg_color=DANGER, hover_color="#e74c3c", text_color=TEXT,
                      font=ctk.CTkFont(size=12),
                      command=lambda: self._delete(item)).pack(side="left")

        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        if item.get("tags"):
            ctk.CTkLabel(self._right, text="Tags: " + ", ".join(item["tags"]),
                         text_color=MUTED, font=ctk.CTkFont(size=11), anchor="w"
                         ).pack(fill="x", padx=16, pady=(0,8))

        md = MarkdownText(self._right, bg=SURFACE2)
        md.pack(fill="both", expand=True, padx=16, pady=(0,16))
        md.set_markdown(item.get("body_md", ""))

    def _new(self):
        self._show_edit({})

    def _show_edit(self, item: dict):
        for w in self._right.winfo_children():
            w.destroy()
        is_new = not item.get("id")

        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        form = {}
        ctk.CTkLabel(hdr, text="New Mechanic" if is_new else "Edit Mechanic",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT, anchor="w"
                     ).pack(side="left")
        ctk.CTkButton(hdr, text="Cancel", width=72, height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=lambda: (self._show_detail(item) if not is_new else self._show_placeholder())
                      ).pack(side="right")
        ctk.CTkButton(hdr, text="Save", width=72, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=lambda: self._save(item.get("id"), form)
                      ).pack(side="right", padx=(0,6))

        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        inner = ctk.CTkFrame(self._right, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=(0,12))
        inner.columnconfigure(1, weight=1)
        inner.rowconfigure(2, weight=1)

        ctk.CTkLabel(inner, text="Title *", text_color=MUTED, font=ctk.CTkFont(size=12),
                     width=90, anchor="e").grid(row=0, column=0, sticky="e", padx=(0,6), pady=4)
        t_var = tk.StringVar(value=item.get("title",""))
        ctk.CTkEntry(inner, textvariable=t_var, fg_color=SURFACE2, border_color=BORDER,
                     text_color=TEXT, height=30).grid(row=0, column=1, sticky="ew", pady=4)
        form["title"] = t_var

        ctk.CTkLabel(inner, text="Campaign", text_color=MUTED, font=ctk.CTkFont(size=12),
                     width=90, anchor="e").grid(row=1, column=0, sticky="e", padx=(0,6), pady=4)
        c_var = tk.StringVar(value=item.get("campaign",""))
        ctk.CTkEntry(inner, textvariable=c_var, fg_color=SURFACE2, border_color=BORDER,
                     text_color=TEXT, height=30, placeholder_text="Optional"
                     ).grid(row=1, column=1, sticky="ew", pady=4)
        form["campaign"] = c_var

        ctk.CTkLabel(inner, text="Tags", text_color=MUTED, font=ctk.CTkFont(size=12),
                     width=90, anchor="e").grid(row=2, column=0, sticky="ne", padx=(0,6), pady=4)
        tg_var = tk.StringVar(value=";".join(item.get("tags",[]) if isinstance(item.get("tags"), list) else []))
        ctk.CTkEntry(inner, textvariable=tg_var, fg_color=SURFACE2, border_color=BORDER,
                     text_color=TEXT, height=30, placeholder_text="Tag1;Tag2"
                     ).grid(row=2, column=1, sticky="ew", pady=4)
        form["tags"] = tg_var

        ctk.CTkLabel(inner, text="Body", text_color=MUTED, font=ctk.CTkFont(size=12),
                     width=90, anchor="ne").grid(row=3, column=0, sticky="ne", padx=(0,6), pady=4)
        tb = ctk.CTkTextbox(inner, fg_color=SURFACE2, border_color=BORDER, text_color=TEXT,
                             font=ctk.CTkFont(size=13), wrap="word")
        tb.insert("1.0", item.get("body_md",""))
        tb.grid(row=3, column=1, sticky="nsew", pady=4)
        inner.rowconfigure(3, weight=1)
        form["body_md"] = tb

    def _save(self, id, form: dict):
        title = form["title"].get().strip()
        if not title:
            messagebox.showerror("Validation", "Title is required."); return
        tags_raw = form["tags"].get().strip()
        tags = [t.strip() for t in tags_raw.replace(";",",").split(",") if t.strip()]
        data = {
            "title": title,
            "campaign": form["campaign"].get().strip() or None,
            "body_md": form["body_md"].get("1.0","end").rstrip(),
            "tags": tags,
        }
        if id:
            self.db.update_mechanic(id, data)
        else:
            id = self.db.create_mechanic(data)
        self.refresh()
        saved = next((it for it in self._items if it["id"] == id), None)
        if saved:
            self._show_detail(saved)

    def _delete(self, item: dict):
        if messagebox.askyesno("Delete", f"Delete '{item['title']}'?"):
            self.db.delete_mechanic(item["id"])
            self.refresh()
            self._show_placeholder()

    def _clear_all(self):
        n = len(self._items)
        if n == 0:
            messagebox.showinfo("Clear All", "No mechanics to clear.")
            return
        if messagebox.askyesno("Clear All Mechanics",
                               f"Permanently delete all {n} mechanic(s)? This cannot be undone."):
            self.db.clear_table("mechanics")
            self.refresh()
            self._show_placeholder()

    def _export(self):
        path = filedialog.asksaveasfilename(
            title="Export Mechanics CSV", defaultextension=".csv",
            filetypes=[("CSV","*.csv")], initialfile="mechanics.csv"
        )
        if path:
            with open(path,"w",newline="",encoding="utf-8") as f:
                f.write(self.db.export_csv("mechanics"))
            messagebox.showinfo("Export", f"Exported to:\n{path}")
