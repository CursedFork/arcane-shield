"""Campaigns page — identical layout to Mechanics but for campaign lore."""
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


class CampaignsPage(ctk.CTkFrame):
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
        ctk.CTkLabel(hdr, text="Campaigns", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="+ New", width=64, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._new).grid(row=0, column=1, sticky="e")
        ctk.CTkButton(hdr, text="Clear All", width=72, height=28,
                      fg_color="transparent", hover_color=DANGER, text_color=MUTED,
                      font=ctk.CTkFont(size=12),
                      command=self._clear_all).grid(row=0, column=2, sticky="e", padx=(4,0))

        flt = ctk.CTkFrame(left, fg_color="transparent")
        flt.grid(row=1, column=0, sticky="ew", padx=12, pady=(0,6))
        flt.columnconfigure(0, weight=1)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._debounce(self._apply_filters))
        ctk.CTkEntry(flt, textvariable=self._search_var, placeholder_text="Search…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=30
                     ).grid(row=0, column=0, sticky="ew", pady=(0,4))

        self._tag_var = tk.StringVar(value="All Tags")
        self._tag_cb = ctk.CTkComboBox(flt, variable=self._tag_var, values=["All Tags"],
                                       fg_color=SURFACE2, border_color=BORDER,
                                       button_color=ACCENT, text_color=TEXT,
                                       dropdown_fg_color=SURFACE2, dropdown_text_color=TEXT,
                                       height=28, font=ctk.CTkFont(size=12),
                                       command=lambda _: self._apply_filters())
        self._tag_cb.grid(row=1, column=0, sticky="ew")

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

    RENDER_CAP = 150

    def _render_list(self):
        body = self._list_frame.body
        self._list_frame.clear()
        for item in self._items[:self.RENDER_CAP]:
            row = tk.Frame(body, bg=SURFACE, cursor="hand2")
            row.pack(fill="x", padx=2, pady=1)
            tk.Label(row, text=item["title"], anchor="w", bg=SURFACE, fg=TEXT,
                     font=("Segoe UI", 11)).pack(side="left", fill="x", expand=True,
                                                 padx=8, pady=6)
            bind_row(row, lambda it=item: self._select(it), SURFACE, SURFACE2)
        if len(self._items) > self.RENDER_CAP:
            tk.Label(body,
                     text=f"Showing {self.RENDER_CAP} of {len(self._items)} — "
                          f"narrow with Search or the filter.",
                     bg=SURFACE, fg=MUTED, font=("Segoe UI", 9), wraplength=240
                     ).pack(fill="x", padx=8, pady=8)
        self._list_frame.finalize()

    def refresh(self):
        self._tag_cb.configure(values=["All Tags"] + self.db.campaign_tags())
        self._apply_filters()

    def _apply_filters(self):
        tag = self._tag_var.get()
        self._items = self.db.list_campaigns(
            search=self._search_var.get().strip(),
            tag="" if tag == "All Tags" else tag,
        )
        self._render_list()

    def _select(self, item: dict):
        self._show_detail(item)

    def _show_placeholder(self):
        for w in self._right.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._right, text="Select a campaign entry to view it",
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

        btn_row = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_row.grid(row=0, column=1, sticky="ne")
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
        md.set_markdown(item.get("body_md",""))

    def _new(self):
        self._show_edit({})

    def _show_edit(self, item: dict):
        for w in self._right.winfo_children():
            w.destroy()
        is_new = not item.get("id")

        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        form = {}
        ctk.CTkLabel(hdr, text="New Campaign" if is_new else "Edit Campaign",
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
                     width=70, anchor="e").grid(row=0, column=0, sticky="e", padx=(0,6), pady=4)
        t_var = tk.StringVar(value=item.get("title",""))
        ctk.CTkEntry(inner, textvariable=t_var, fg_color=SURFACE2, border_color=BORDER,
                     text_color=TEXT, height=30).grid(row=0, column=1, sticky="ew", pady=4)
        form["title"] = t_var

        ctk.CTkLabel(inner, text="Tags", text_color=MUTED, font=ctk.CTkFont(size=12),
                     width=70, anchor="e").grid(row=1, column=0, sticky="e", padx=(0,6), pady=4)
        tg_var = tk.StringVar(value=";".join(item.get("tags",[]) if isinstance(item.get("tags"), list) else []))
        ctk.CTkEntry(inner, textvariable=tg_var, fg_color=SURFACE2, border_color=BORDER,
                     text_color=TEXT, height=30, placeholder_text="Tag1;Tag2"
                     ).grid(row=1, column=1, sticky="ew", pady=4)
        form["tags"] = tg_var

        ctk.CTkLabel(inner, text="Body", text_color=MUTED, font=ctk.CTkFont(size=12),
                     width=70, anchor="ne").grid(row=2, column=0, sticky="ne", padx=(0,6), pady=4)
        tb = ctk.CTkTextbox(inner, fg_color=SURFACE2, border_color=BORDER, text_color=TEXT,
                             font=ctk.CTkFont(size=13), wrap="word")
        tb.insert("1.0", item.get("body_md",""))
        tb.grid(row=2, column=1, sticky="nsew", pady=4)
        inner.rowconfigure(2, weight=1)
        form["body_md"] = tb

    def _save(self, id, form: dict):
        title = form["title"].get().strip()
        if not title:
            messagebox.showerror("Validation", "Title is required."); return
        tags_raw = form["tags"].get().strip()
        tags = [t.strip() for t in tags_raw.replace(";",",").split(",") if t.strip()]
        data = {
            "title": title,
            "body_md": form["body_md"].get("1.0","end").rstrip(),
            "tags": tags,
        }
        if id:
            self.db.update_campaign(id, data)
        else:
            id = self.db.create_campaign(data)
        self.refresh()
        saved = next((it for it in self._items if it["id"] == id), None)
        if saved:
            self._show_detail(saved)

    def _delete(self, item: dict):
        if messagebox.askyesno("Delete", f"Delete '{item['title']}'?"):
            self.db.delete_campaign(item["id"])
            self.refresh()
            self._show_placeholder()

    def _clear_all(self):
        n = len(self.db.list_campaigns())  # whole table, not the filtered view
        if n == 0:
            messagebox.showinfo("Clear All", "No campaigns to clear.")
            return
        if messagebox.askyesno("Clear All Campaigns",
                               f"Permanently delete ALL {n} campaign(s) (the entire table)? This cannot be undone."):
            self.db.clear_table("campaigns")
            self.refresh()
            self._show_placeholder()

    def _export(self):
        path = filedialog.asksaveasfilename(
            title="Export Campaigns CSV", defaultextension=".csv",
            filetypes=[("CSV","*.csv")], initialfile="campaigns.csv"
        )
        if path:
            with open(path,"w",newline="",encoding="utf-8") as f:
                f.write(self.db.export_csv("campaigns"))
            messagebox.showinfo("Export", f"Exported to:\n{path}")
