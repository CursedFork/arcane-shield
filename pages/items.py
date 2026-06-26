"""Magic Items page."""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog

BG       = "#0f0f13"
SURFACE  = "#1a1a24"
SURFACE2 = "#22222f"
BORDER   = "#2e2e3e"
ACCENT   = "#7c5cbf"
ACCENT_H = "#9472d8"
TEXT     = "#e2e0f0"
MUTED    = "#8a8aa0"
DANGER   = "#c0392b"
SUCCESS  = "#27ae60"

RARITIES = ["Common", "Uncommon", "Rare", "Very Rare", "Legendary", "Artifact"]
RARITY_COLORS = {
    "Common": "#aaaaaa", "Uncommon": "#1eff00", "Rare": "#0070dd",
    "Very Rare": "#a335ee", "Legendary": "#ff8000", "Artifact": "#e6cc80",
}


class ItemsPage(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._items: list[dict] = []
        self._selected: dict | None = None
        self._editing = False
        self._build()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Left panel ─────────────────────────────────────────────────────────
        left = ctk.CTkFrame(self, width=300, fg_color=SURFACE, corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(16,8), pady=16)
        left.grid_propagate(False)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Header row
        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,6))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="Magic Items", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="+ New", width=64, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT,
                      font=ctk.CTkFont(size=12),
                      command=self._new_item).grid(row=0, column=1, sticky="e")
        ctk.CTkButton(hdr, text="Clear All", width=72, height=28,
                      fg_color="transparent", hover_color=DANGER, text_color=MUTED,
                      font=ctk.CTkFont(size=12),
                      command=self._clear_all).grid(row=0, column=2, sticky="e", padx=(4,0))

        # Search + filters
        flt = ctk.CTkFrame(left, fg_color="transparent")
        flt.grid(row=1, column=0, sticky="ew", padx=12, pady=(0,6))
        flt.columnconfigure(0, weight=1)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filters())
        ctk.CTkEntry(flt, textvariable=self._search_var, placeholder_text="Search…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT,
                     height=30).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0,4))

        self._type_var = tk.StringVar(value="All Types")
        self._type_cb = ctk.CTkComboBox(flt, variable=self._type_var, values=["All Types"],
                                         fg_color=SURFACE2, border_color=BORDER,
                                         button_color=ACCENT, text_color=TEXT,
                                         dropdown_fg_color=SURFACE2, dropdown_text_color=TEXT,
                                         height=28, font=ctk.CTkFont(size=12),
                                         command=lambda _: self._apply_filters())
        self._type_cb.grid(row=1, column=0, sticky="ew", padx=(0,3))

        self._rarity_var = tk.StringVar(value="All Rarities")
        ctk.CTkComboBox(flt, variable=self._rarity_var,
                        values=["All Rarities"] + RARITIES,
                        fg_color=SURFACE2, border_color=BORDER,
                        button_color=ACCENT, text_color=TEXT,
                        dropdown_fg_color=SURFACE2, dropdown_text_color=TEXT,
                        height=28, font=ctk.CTkFont(size=12),
                        command=lambda _: self._apply_filters()
                        ).grid(row=1, column=1, sticky="ew", padx=(3,0))

        self._attune_var = tk.StringVar(value="Any Attunement")
        ctk.CTkComboBox(flt, variable=self._attune_var,
                        values=["Any Attunement", "Requires Attunement", "No Attunement"],
                        fg_color=SURFACE2, border_color=BORDER,
                        button_color=ACCENT, text_color=TEXT,
                        dropdown_fg_color=SURFACE2, dropdown_text_color=TEXT,
                        height=28, font=ctk.CTkFont(size=12),
                        command=lambda _: self._apply_filters()
                        ).grid(row=2, column=0, sticky="ew", padx=(0,3), pady=(4,0))

        self._tag_var = tk.StringVar(value="All Tags")
        self._tag_cb = ctk.CTkComboBox(flt, variable=self._tag_var, values=["All Tags"],
                                       fg_color=SURFACE2, border_color=BORDER,
                                       button_color=ACCENT, text_color=TEXT,
                                       dropdown_fg_color=SURFACE2, dropdown_text_color=TEXT,
                                       height=28, font=ctk.CTkFont(size=12),
                                       command=lambda _: self._apply_filters())
        self._tag_cb.grid(row=2, column=1, sticky="ew", padx=(3,0), pady=(4,0))

        # Item list
        self._list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent",
                                                   scrollbar_button_color=ACCENT)
        self._list_frame.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0,4))
        self._list_frame.columnconfigure(0, weight=1)

        # Export button
        ctk.CTkButton(left, text="Export CSV", height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=self._export).grid(row=3, column=0, sticky="ew", padx=12, pady=(0,12))

        # ── Right panel ────────────────────────────────────────────────────────
        self._right = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        self._right.grid(row=0, column=1, sticky="nsew", padx=(8,16), pady=16)
        self._right.grid_columnconfigure(0, weight=1)
        self._right.grid_rowconfigure(1, weight=1)
        self._show_placeholder()

    # ── List rendering ─────────────────────────────────────────────────────────

    RENDER_CAP = 300

    def _render_list(self, items: list[dict]):
        for w in self._list_frame.winfo_children():
            w.destroy()
        for item in items[:self.RENDER_CAP]:
            color = RARITY_COLORS.get(item.get("rarity", "Common"), MUTED)
            row = ctk.CTkFrame(self._list_frame, fg_color="transparent", corner_radius=4,
                                cursor="hand2")
            row.pack(fill="x", padx=2, pady=1)
            row.columnconfigure(1, weight=1)
            # Rarity dot
            ctk.CTkLabel(row, text="●", text_color=color,
                         font=ctk.CTkFont(size=10), width=14).grid(row=0, column=0, padx=(4,2))
            ctk.CTkLabel(row, text=item["name"], anchor="w",
                         text_color=TEXT, font=ctk.CTkFont(size=13),
                         wraplength=200).grid(row=0, column=1, sticky="ew", pady=5)
            ctk.CTkLabel(row, text=item.get("item_type",""), anchor="e",
                         text_color=MUTED, font=ctk.CTkFont(size=11)).grid(row=0, column=2, padx=(0,6))
            row.bind("<Button-1>", lambda e, it=item: self._select(it))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, it=item: self._select(it))
        if len(items) > self.RENDER_CAP:
            ctk.CTkLabel(self._list_frame,
                         text=f"Showing {self.RENDER_CAP} of {len(items)} — "
                              f"use Search or the filters to narrow results.",
                         text_color=MUTED, font=ctk.CTkFont(size=11), wraplength=240
                         ).pack(fill="x", padx=8, pady=8)

    def _apply_filters(self):
        search = self._search_var.get().strip()
        rtype = self._type_var.get()
        rarity = self._rarity_var.get()
        attune = {"Requires Attunement": "yes", "No Attunement": "no"}.get(
            self._attune_var.get(), "")
        tag = self._tag_var.get()
        items = self.db.list_items(
            search=search,
            item_type="" if rtype == "All Types" else rtype,
            rarity="" if rarity == "All Rarities" else rarity,
            attunement=attune,
            tag="" if tag == "All Tags" else tag,
        )
        self._items = items
        self._render_list(items)

    def refresh(self):
        types = self.db.item_types()
        self._type_cb.configure(values=["All Types"] + types)
        self._tag_cb.configure(values=["All Tags"] + self.db.item_tags())
        self._apply_filters()

    # ── Selection / Detail ─────────────────────────────────────────────────────

    def _select(self, item: dict):
        self._selected = item
        self._editing = False
        self._show_detail(item)

    def _show_placeholder(self):
        for w in self._right.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._right, text="Select an item to view details",
                     text_color=MUTED, font=ctk.CTkFont(size=13)).pack(expand=True)

    def _show_detail(self, item: dict):
        for w in self._right.winfo_children():
            w.destroy()

        # Header
        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        hdr.columnconfigure(0, weight=1)

        rcolor = RARITY_COLORS.get(item.get("rarity","Common"), MUTED)
        ctk.CTkLabel(hdr, text=item["name"],
                     font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT,
                     anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(hdr, text=item.get("rarity","Common"), text_color=rcolor,
                     font=ctk.CTkFont(size=12)).grid(row=1, column=0, sticky="w")

        # Action buttons
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

        # Separator
        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        # Scrollable body
        body = ctk.CTkScrollableFrame(self._right, fg_color="transparent",
                                       scrollbar_button_color=ACCENT)
        body.pack(fill="both", expand=True, padx=8, pady=(0,8))
        body.columnconfigure(1, weight=1)

        def field(label, val, row):
            if not val and val != 0:
                return
            ctk.CTkLabel(body, text=label+":", text_color=MUTED,
                         font=ctk.CTkFont(size=12), anchor="ne",
                         width=130).grid(row=row, column=0, sticky="ne", padx=(8,4), pady=3)
            ctk.CTkLabel(body, text=str(val), text_color=TEXT, wraplength=420,
                         anchor="nw", justify="left",
                         font=ctk.CTkFont(size=12)).grid(row=row, column=1, sticky="nw", pady=3)

        r = 0
        field("Type", item.get("item_type",""), r); r+=1
        if item.get("requires_attunement"):
            req = item.get("attunement_requirement","")
            field("Attunement", req if req else "Yes", r); r+=1
        if item.get("charges"):
            field("Charges", item["charges"], r); r+=1
        if item.get("source_campaign"):
            field("Campaign", item["source_campaign"], r); r+=1
        if item.get("tags"):
            field("Tags", ", ".join(item["tags"]), r); r+=1

        if item.get("description"):
            ctk.CTkLabel(body, text="Description", text_color=MUTED,
                         font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=r, column=0, columnspan=2, sticky="w", padx=8, pady=(8,2)); r+=1
            tb = ctk.CTkTextbox(body, height=100, fg_color=SURFACE2, text_color=TEXT,
                                 border_color=BORDER, font=ctk.CTkFont(size=12), wrap="word")
            tb.insert("1.0", item["description"])
            tb.configure(state="disabled")
            tb.grid(row=r, column=0, columnspan=2, sticky="ew", padx=8, pady=(0,6)); r+=1

        if item.get("mechanical_effect"):
            ctk.CTkLabel(body, text="Mechanical Effect", text_color=MUTED,
                         font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=r, column=0, columnspan=2, sticky="w", padx=8, pady=(8,2)); r+=1
            tb2 = ctk.CTkTextbox(body, height=120, fg_color=SURFACE2, text_color=TEXT,
                                  border_color=BORDER, font=ctk.CTkFont(size=12), wrap="word")
            tb2.insert("1.0", item["mechanical_effect"])
            tb2.configure(state="disabled")
            tb2.grid(row=r, column=0, columnspan=2, sticky="ew", padx=8, pady=(0,8)); r+=1

    # ── Edit form ──────────────────────────────────────────────────────────────

    def _new_item(self):
        self._selected = None
        self._show_edit({})

    def _show_edit(self, item: dict):
        for w in self._right.winfo_children():
            w.destroy()

        is_new = not item.get("id")
        title = "New Item" if is_new else f"Edit: {item.get('name','')}"

        # Header
        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        ctk.CTkLabel(hdr, text=title, font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=TEXT, anchor="w").pack(side="left")
        ctk.CTkButton(hdr, text="Cancel", width=72, height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=lambda: (self._show_detail(item) if not is_new else self._show_placeholder())
                      ).pack(side="right")
        ctk.CTkButton(hdr, text="Save", width=72, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=lambda: self._save(item.get("id"), form)
                      ).pack(side="right", padx=(0,6))

        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        # Form
        scroll = ctk.CTkScrollableFrame(self._right, fg_color="transparent",
                                         scrollbar_button_color=ACCENT)
        scroll.pack(fill="both", expand=True, padx=8, pady=(0,8))
        scroll.columnconfigure(1, weight=1)

        form: dict[str, tk.Variable | ctk.CTkTextbox] = {}

        def lbl_entry(label, key, row, default="", placeholder=""):
            ctk.CTkLabel(scroll, text=label, text_color=MUTED,
                         font=ctk.CTkFont(size=12), width=140, anchor="e"
                         ).grid(row=row, column=0, sticky="e", padx=(8,6), pady=4)
            var = tk.StringVar(value=str(item.get(key, default)))
            ctk.CTkEntry(scroll, textvariable=var, fg_color=SURFACE2,
                         border_color=BORDER, text_color=TEXT,
                         placeholder_text=placeholder, height=30
                         ).grid(row=row, column=1, sticky="ew", padx=(0,8), pady=4)
            form[key] = var
            return var

        def lbl_combo(label, key, row, values, default=""):
            ctk.CTkLabel(scroll, text=label, text_color=MUTED,
                         font=ctk.CTkFont(size=12), width=140, anchor="e"
                         ).grid(row=row, column=0, sticky="e", padx=(8,6), pady=4)
            var = tk.StringVar(value=str(item.get(key, default)))
            ctk.CTkComboBox(scroll, variable=var, values=values,
                            fg_color=SURFACE2, border_color=BORDER, button_color=ACCENT,
                            text_color=TEXT, dropdown_fg_color=SURFACE2,
                            dropdown_text_color=TEXT, height=30
                            ).grid(row=row, column=1, sticky="ew", padx=(0,8), pady=4)
            form[key] = var
            return var

        def lbl_textbox(label, key, row, height=80):
            ctk.CTkLabel(scroll, text=label, text_color=MUTED,
                         font=ctk.CTkFont(size=12), width=140, anchor="ne"
                         ).grid(row=row, column=0, sticky="ne", padx=(8,6), pady=4)
            tb = ctk.CTkTextbox(scroll, height=height, fg_color=SURFACE2,
                                 border_color=BORDER, text_color=TEXT,
                                 font=ctk.CTkFont(size=12), wrap="word")
            tb.insert("1.0", item.get(key,""))
            tb.grid(row=row, column=1, sticky="ew", padx=(0,8), pady=4)
            form[key] = tb
            return tb

        r = 0
        lbl_entry("Name *", "name", r, placeholder="Item name"); r+=1
        lbl_entry("Type", "item_type", r, placeholder="Weapon, Armor, Wondrous…"); r+=1
        lbl_combo("Rarity", "rarity", r, RARITIES, "Common"); r+=1

        # Requires attunement checkbox
        ctk.CTkLabel(scroll, text="Attunement", text_color=MUTED,
                     font=ctk.CTkFont(size=12), width=140, anchor="e"
                     ).grid(row=r, column=0, sticky="e", padx=(8,6), pady=4)
        att_var = tk.BooleanVar(value=bool(item.get("requires_attunement", False)))
        ctk.CTkCheckBox(scroll, text="Requires attunement",
                        variable=att_var, text_color=TEXT,
                        checkbox_width=18, checkbox_height=18,
                        fg_color=ACCENT, hover_color=ACCENT_H, border_color=BORDER
                        ).grid(row=r, column=1, sticky="w", padx=(0,8), pady=4)
        form["requires_attunement"] = att_var; r+=1

        lbl_entry("Att. Requirement", "attunement_requirement", r,
                  placeholder="by a warlock, spellcaster…"); r+=1
        lbl_entry("Charges", "charges", r, placeholder="Optional"); r+=1
        lbl_entry("Source Campaign", "source_campaign", r, placeholder="Optional"); r+=1
        lbl_entry("Tags", "tags", r, placeholder="Semicolon-separated: Combat;Fire"); r+=1
        lbl_textbox("Description", "description", r, 100); r+=1
        lbl_textbox("Mechanical Effect", "mechanical_effect", r, 120); r+=1

        # Pre-fill tags as semicolon string
        if "tags" in form and isinstance(item.get("tags"), list):
            form["tags"].set(";".join(item["tags"]))

    def _save(self, id, form: dict):
        name = form["name"].get().strip() if isinstance(form["name"], tk.StringVar) else ""
        if not name:
            messagebox.showerror("Validation", "Name is required."); return

        def val(key):
            v = form.get(key)
            if v is None: return ""
            if isinstance(v, tk.BooleanVar): return v.get()
            if isinstance(v, ctk.CTkTextbox): return v.get("1.0", "end").rstrip()
            return v.get().strip()

        tags_raw = val("tags")
        tags = [t.strip() for t in tags_raw.replace(";", ",").split(",") if t.strip()] if tags_raw else []

        data = {
            "name": name,
            "item_type": val("item_type"),
            "rarity": val("rarity") or "Common",
            "requires_attunement": val("requires_attunement"),
            "attunement_requirement": val("attunement_requirement") or None,
            "description": val("description"),
            "mechanical_effect": val("mechanical_effect"),
            "charges": val("charges") or None,
            "source_campaign": val("source_campaign") or None,
            "tags": tags,
        }

        if id:
            self.db.update_item(id, data)
        else:
            id = self.db.create_item(data)

        self.refresh()
        # Re-select saved item
        saved = next((it for it in self._items if it["id"] == id), None)
        if saved:
            self._show_detail(saved)
        else:
            self._show_placeholder()

    def _delete(self, item: dict):
        if messagebox.askyesno("Delete", f"Delete '{item['name']}'? This cannot be undone."):
            self.db.delete_item(item["id"])
            self._selected = None
            self.refresh()
            self._show_placeholder()

    def _clear_all(self):
        n = len(self._items)
        if n == 0:
            messagebox.showinfo("Clear All", "No magic items to clear.")
            return
        if messagebox.askyesno("Clear All Magic Items",
                               f"Permanently delete all {n} item(s)? This cannot be undone."):
            self.db.clear_table("magic_items")
            self._selected = None
            self.refresh()
            self._show_placeholder()

    def _export(self):
        path = filedialog.asksaveasfilename(
            title="Export Magic Items CSV",
            defaultextension=".csv",
            filetypes=[("CSV files","*.csv")],
            initialfile="magic_items.csv"
        )
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write(self.db.export_csv("magic_items"))
            messagebox.showinfo("Export", f"Exported to:\n{path}")
