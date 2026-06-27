"""Languages page — D&D 5e languages reference."""
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

CATEGORIES = ["Standard", "Exotic", "Secret"]
CAT_COLORS = {"Standard": "#5dade2", "Exotic": "#bb8fce", "Secret": "#f5b041"}


class LanguagesPage(ctk.CTkFrame):
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
        left.grid_rowconfigure(3, weight=1)
        left.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,6))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="Languages", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="+ New", width=64, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._new).grid(row=0, column=1, sticky="e")

        flt = ctk.CTkFrame(left, fg_color="transparent")
        flt.grid(row=1, column=0, sticky="ew", padx=12, pady=(0,6))
        flt.columnconfigure(0, weight=1)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._debounce(self._apply_filters))
        ctk.CTkEntry(flt, textvariable=self._search_var, placeholder_text="Search…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=30
                     ).grid(row=0, column=0, sticky="ew", pady=(0,4))
        self._cat_var = tk.StringVar(value="All Categories")
        ctk.CTkComboBox(flt, variable=self._cat_var, values=["All Categories"] + CATEGORIES,
                        fg_color=SURFACE2, border_color=BORDER, button_color=ACCENT,
                        text_color=TEXT, dropdown_fg_color=SURFACE2, dropdown_text_color=TEXT,
                        height=28, font=ctk.CTkFont(size=12),
                        command=lambda _: self._apply_filters()).grid(row=1, column=0, sticky="ew")
        ctk.CTkButton(flt, text="⟲ Reset filters", height=24, fg_color="transparent",
                      hover_color=SURFACE2, text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=self._reset_filters).grid(row=2, column=0, sticky="e", pady=(4,0))

        self._list_frame = ScrollList(left, bg=SURFACE, accent=ACCENT)
        self._list_frame.grid(row=3, column=0, sticky="nsew", padx=4, pady=(0,12))

        self._right = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        self._right.grid(row=0, column=1, sticky="nsew", padx=(8,16), pady=16)
        self._right.grid_columnconfigure(0, weight=1)
        self._right.grid_rowconfigure(1, weight=1)
        self._show_placeholder()

    def _render_list(self):
        body = self._list_frame.body
        self._list_frame.clear()
        for lang in self._items:
            color = CAT_COLORS.get(lang.get("category", ""), MUTED)
            row = tk.Frame(body, bg=SURFACE, cursor="hand2")
            row.pack(fill="x", padx=2, pady=1)
            tk.Label(row, text=lang.get("category", ""), anchor="e", fg=color, bg=SURFACE,
                     font=("Segoe UI", 8)).pack(side="right", padx=6)
            tk.Label(row, text=lang["name"], anchor="w", fg=TEXT, bg=SURFACE,
                     font=("Segoe UI", 11)).pack(side="left", fill="x", expand=True,
                                                 padx=8, pady=6)
            bind_row(row, lambda x=lang: self._show_detail(x), SURFACE, SURFACE2)
        self._list_frame.finalize()

    def refresh(self):
        self._apply_filters()

    def _apply_filters(self):
        cat = self._cat_var.get()
        self._items = self.db.list_languages(
            search=self._search_var.get().strip(),
            category="" if cat == "All Categories" else cat,
        )
        self._render_list()

    def _reset_filters(self):
        self._search_var.set("")
        self._cat_var.set("All Categories")
        self._apply_filters()

    def _show_placeholder(self):
        for w in self._right.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._right, text="Select a language to view it",
                     text_color=MUTED, font=ctk.CTkFont(size=13)).pack(expand=True)

    def _show_detail(self, lang: dict):
        for w in self._right.winfo_children():
            w.destroy()
        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        hdr.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text=lang["name"], font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT, anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(hdr, text=lang.get("category", ""),
                     text_color=CAT_COLORS.get(lang.get("category",""), MUTED),
                     font=ctk.CTkFont(size=12), anchor="w").grid(row=1, column=0, sticky="w")
        btns = ctk.CTkFrame(hdr, fg_color="transparent")
        btns.grid(row=0, column=1, rowspan=2, sticky="ne")
        ctk.CTkButton(btns, text="Edit", width=64, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=lambda: self._show_edit(lang)).pack(side="left", padx=(0,4))
        ctk.CTkButton(btns, text="Delete", width=64, height=28, fg_color=DANGER,
                      hover_color="#e74c3c", text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=lambda: self._delete(lang)).pack(side="left")
        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        meta = ctk.CTkFrame(self._right, fg_color="transparent")
        meta.pack(fill="x", padx=16, pady=(0,6))
        meta.columnconfigure(1, weight=1)
        r = 0
        for label, key in [("Script", "script"), ("Typical Speakers", "typical_speakers")]:
            val = lang.get(key)
            if not val:
                continue
            ctk.CTkLabel(meta, text=label, text_color=MUTED, font=ctk.CTkFont(size=11),
                         width=120, anchor="w").grid(row=r, column=0, sticky="w", pady=1)
            ctk.CTkLabel(meta, text=str(val), text_color=TEXT, font=ctk.CTkFont(size=12),
                         anchor="w", wraplength=420, justify="left"
                         ).grid(row=r, column=1, sticky="w", pady=1)
            r += 1

        md = MarkdownText(self._right, bg=SURFACE2)
        md.pack(fill="both", expand=True, padx=16, pady=(6,16))
        md.set_markdown(lang.get("description", "") or "*(no description)*")

    def _new(self):
        self._show_edit({})

    def _show_edit(self, lang: dict):
        for w in self._right.winfo_children():
            w.destroy()
        is_new = not lang.get("id")
        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        ctk.CTkLabel(hdr, text="New Language" if is_new else f"Edit: {lang.get('name','')}",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT, anchor="w"
                     ).pack(side="left")
        ctk.CTkButton(hdr, text="Cancel", width=72, height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=lambda: (self._show_detail(lang) if not is_new else self._show_placeholder())
                      ).pack(side="right")

        form = ctk.CTkScrollableFrame(self._right, fg_color="transparent",
                                      scrollbar_button_color=ACCENT)
        name_var = tk.StringVar(value=lang.get("name", ""))
        cat_var = tk.StringVar(value=lang.get("category", "Standard"))
        script_var = tk.StringVar(value=lang.get("script", ""))
        speakers_var = tk.StringVar(value=lang.get("typical_speakers", ""))

        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Validation", "Name is required."); return
            data = {"name": name, "category": cat_var.get(), "script": script_var.get().strip(),
                    "typical_speakers": speakers_var.get().strip(),
                    "description": desc.get("1.0", "end").rstrip()}
            if lang.get("id"):
                self.db.update_language(lang["id"], data)
            else:
                self.db.create_language(data)
            self.refresh()
            saved = next((x for x in self._items if x["name"] == name), None)
            if saved:
                self._show_detail(saved)

        ctk.CTkButton(hdr, text="Save", width=72, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=save).pack(side="right", padx=(0,6))
        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        form.pack(fill="both", expand=True, padx=8, pady=(0,12))
        form.columnconfigure(1, weight=1)

        def row(r, label, widget):
            ctk.CTkLabel(form, text=label, text_color=MUTED, font=ctk.CTkFont(size=12),
                         width=120, anchor="e").grid(row=r, column=0, sticky="e", padx=(8,4), pady=3)
            widget.grid(row=r, column=1, sticky="ew", pady=3)

        row(0, "Name", ctk.CTkEntry(form, textvariable=name_var, fg_color=SURFACE2,
                                    border_color=BORDER, text_color=TEXT, height=28))
        row(1, "Category", ctk.CTkOptionMenu(form, variable=cat_var, values=CATEGORIES,
                                             fg_color=SURFACE2, button_color=ACCENT,
                                             button_hover_color=ACCENT_H, text_color=TEXT))
        row(2, "Script", ctk.CTkEntry(form, textvariable=script_var, fg_color=SURFACE2,
                                      border_color=BORDER, text_color=TEXT, height=28))
        row(3, "Typical Speakers", ctk.CTkEntry(form, textvariable=speakers_var, fg_color=SURFACE2,
                                                border_color=BORDER, text_color=TEXT, height=28))
        ctk.CTkLabel(form, text="Description", text_color=MUTED, font=ctk.CTkFont(size=12),
                     anchor="e", width=120).grid(row=4, column=0, sticky="ne", padx=(8,4), pady=3)
        desc = ctk.CTkTextbox(form, height=140, fg_color=SURFACE2, border_color=BORDER,
                              text_color=TEXT, font=ctk.CTkFont(size=12), wrap="word")
        desc.insert("1.0", lang.get("description", ""))
        desc.grid(row=4, column=1, sticky="nsew", pady=3)
        form.rowconfigure(4, weight=1)

    def _delete(self, lang: dict):
        if messagebox.askyesno("Delete", f"Delete '{lang['name']}'?"):
            self.db.delete_language(lang["id"])
            self.refresh()
            self._show_placeholder()
