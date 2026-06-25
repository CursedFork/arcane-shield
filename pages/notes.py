"""Session Notes page."""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import date

BG       = "#0f0f13"
SURFACE  = "#1a1a24"
SURFACE2 = "#22222f"
BORDER   = "#2e2e3e"
ACCENT   = "#7c5cbf"
ACCENT_H = "#9472d8"
TEXT     = "#e2e0f0"
MUTED    = "#8a8aa0"
DANGER   = "#c0392b"


class NotesPage(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._notes: list[dict] = []
        self._selected: dict | None = None
        self._build()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Left: quick-add + list ─────────────────────────────────────────────
        left = ctk.CTkFrame(self, width=300, fg_color=SURFACE, corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(16,8), pady=16)
        left.grid_propagate(False)
        left.grid_rowconfigure(3, weight=1)
        left.grid_columnconfigure(0, weight=1)

        hdr_row = ctk.CTkFrame(left, fg_color="transparent")
        hdr_row.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,8))
        hdr_row.columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr_row, text="Session Notes", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr_row, text="Clear All", width=72, height=28,
                      fg_color="transparent", hover_color=DANGER, text_color=MUTED,
                      font=ctk.CTkFont(size=12),
                      command=self._clear_all).grid(row=0, column=1, sticky="e")

        # Quick-add form
        add_frame = ctk.CTkFrame(left, fg_color=SURFACE2, corner_radius=6)
        add_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0,8))
        add_frame.columnconfigure(0, weight=1)

        ctk.CTkLabel(add_frame, text="Add Note", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=ACCENT).grid(row=0, column=0, sticky="w", padx=10, pady=(8,4))

        self._sl_var = tk.StringVar(value="Session 1")
        ctk.CTkEntry(add_frame, textvariable=self._sl_var, placeholder_text="Session label",
                     fg_color=SURFACE, border_color=BORDER, text_color=TEXT, height=28
                     ).grid(row=1, column=0, sticky="ew", padx=10, pady=(0,4))

        self._date_var = tk.StringVar(value=str(date.today()))
        ctk.CTkEntry(add_frame, textvariable=self._date_var, placeholder_text="YYYY-MM-DD",
                     fg_color=SURFACE, border_color=BORDER, text_color=TEXT, height=28
                     ).grid(row=2, column=0, sticky="ew", padx=10, pady=(0,4))

        self._body_tb = ctk.CTkTextbox(add_frame, height=80, fg_color=SURFACE,
                                        border_color=BORDER, text_color=TEXT,
                                        font=ctk.CTkFont(size=12), wrap="word")
        self._body_tb.grid(row=3, column=0, sticky="ew", padx=10, pady=(0,4))

        ctk.CTkButton(add_frame, text="Add Note", height=30, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._add_note).grid(row=4, column=0, sticky="ew", padx=10, pady=(0,10))

        # Filters
        flt = ctk.CTkFrame(left, fg_color="transparent")
        flt.grid(row=2, column=0, sticky="ew", padx=12, pady=(0,6))
        flt.columnconfigure((0, 1), weight=1)

        self._filter_session_var = tk.StringVar(value="All Sessions")
        self._session_cb = ctk.CTkComboBox(flt, variable=self._filter_session_var,
                                           values=["All Sessions"],
                                           fg_color=SURFACE2, border_color=BORDER,
                                           button_color=ACCENT, text_color=TEXT,
                                           dropdown_fg_color=SURFACE2, dropdown_text_color=TEXT,
                                           height=28, font=ctk.CTkFont(size=12),
                                           command=lambda _: self.refresh())
        self._session_cb.grid(row=0, column=0, sticky="ew", padx=(0,3))

        self._filter_date_var = tk.StringVar()
        self._filter_date_var.trace_add("write", lambda *_: self.refresh())
        ctk.CTkEntry(flt, textvariable=self._filter_date_var,
                     placeholder_text="Date (YYYY, YYYY-MM…)",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=28
                     ).grid(row=0, column=1, sticky="ew", padx=(3,0))

        # List
        self._list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent",
                                                   scrollbar_button_color=ACCENT)
        self._list_frame.grid(row=3, column=0, sticky="nsew", padx=4, pady=(0,4))
        self._list_frame.columnconfigure(0, weight=1)

        ctk.CTkButton(left, text="Export CSV", height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=self._export).grid(row=4, column=0, sticky="ew", padx=12, pady=(0,12))

        # ── Right: note detail / edit ──────────────────────────────────────────
        self._right = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        self._right.grid(row=0, column=1, sticky="nsew", padx=(8,16), pady=16)
        self._right.grid_columnconfigure(0, weight=1)
        self._right.grid_rowconfigure(0, weight=1)
        self._show_placeholder()

    def _render_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

        # Group by session label
        sessions: dict[str, list[dict]] = {}
        for n in self._notes:
            sessions.setdefault(n["session_label"], []).append(n)

        for session, notes in sessions.items():
            ctk.CTkLabel(self._list_frame, text=session,
                         font=ctk.CTkFont(size=12, weight="bold"), text_color=ACCENT,
                         anchor="w").pack(fill="x", padx=8, pady=(8,2))
            for note in notes:
                row = ctk.CTkFrame(self._list_frame, fg_color=SURFACE2, corner_radius=4,
                                   cursor="hand2")
                row.pack(fill="x", padx=4, pady=2)
                row.columnconfigure(0, weight=1)
                preview = note.get("body","")[:60].replace("\n"," ")
                if len(note.get("body","")) > 60:
                    preview += "…"
                ctk.CTkLabel(row, text=preview, anchor="w", text_color=TEXT,
                             font=ctk.CTkFont(size=12), wraplength=220
                             ).grid(row=0, column=0, sticky="ew", padx=8, pady=(5,2))
                ctk.CTkLabel(row, text=note.get("note_date",""), anchor="w",
                             text_color=MUTED, font=ctk.CTkFont(size=10)
                             ).grid(row=1, column=0, sticky="w", padx=8, pady=(0,5))
                row.bind("<Button-1>", lambda e, n=note: self._select(n))
                for c in row.winfo_children():
                    c.bind("<Button-1>", lambda e, n=note: self._select(n))

    def refresh(self):
        self._session_cb.configure(values=["All Sessions"] + self.db.note_sessions())
        session = self._filter_session_var.get()
        self._notes = self.db.list_notes(
            session_label="" if session == "All Sessions" else session,
            date_prefix=self._filter_date_var.get().strip(),
        )
        self._render_list()

    def _select(self, note: dict):
        self._selected = note
        self._show_detail(note)

    def _show_placeholder(self):
        for w in self._right.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._right, text="Select a note to view it, or add one on the left",
                     text_color=MUTED, font=ctk.CTkFont(size=13)).pack(expand=True)

    def _show_detail(self, note: dict):
        for w in self._right.winfo_children():
            w.destroy()

        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        hdr.columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr, text=note["session_label"],
                     font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT, anchor="w"
                     ).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(hdr, text=note.get("note_date",""), text_color=MUTED,
                     font=ctk.CTkFont(size=12), anchor="w").grid(row=1, column=0, sticky="w")

        btn_row = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_row.grid(row=0, column=1, rowspan=2, sticky="ne")
        ctk.CTkButton(btn_row, text="Edit", width=64, height=28,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=TEXT,
                      font=ctk.CTkFont(size=12),
                      command=lambda: self._show_edit(note)).pack(side="left", padx=(0,4))
        ctk.CTkButton(btn_row, text="Delete", width=64, height=28,
                      fg_color=DANGER, hover_color="#e74c3c", text_color=TEXT,
                      font=ctk.CTkFont(size=12),
                      command=lambda: self._delete(note)).pack(side="left")

        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        tb = ctk.CTkTextbox(self._right, fg_color=SURFACE2, text_color=TEXT,
                             border_color=BORDER, font=ctk.CTkFont(size=13), wrap="word")
        tb.pack(fill="both", expand=True, padx=16, pady=(0,16))
        tb.insert("1.0", note.get("body",""))
        tb.configure(state="disabled")

    def _show_edit(self, note: dict):
        for w in self._right.winfo_children():
            w.destroy()

        hdr = ctk.CTkFrame(self._right, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16,8))
        form = {}
        ctk.CTkLabel(hdr, text="Edit Note", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=TEXT, anchor="w").pack(side="left")
        ctk.CTkButton(hdr, text="Cancel", width=72, height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=lambda: self._show_detail(note)).pack(side="right")
        ctk.CTkButton(hdr, text="Save", width=72, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=lambda: self._save_edit(note["id"], form)).pack(side="right", padx=(0,6))

        ctk.CTkFrame(self._right, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0,8))

        inner = ctk.CTkFrame(self._right, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=(0,12))
        inner.columnconfigure(1, weight=1)
        inner.rowconfigure(2, weight=1)

        for r, (label, key, default) in enumerate([
            ("Session", "session_label", note.get("session_label","")),
            ("Date", "note_date", note.get("note_date","")),
        ]):
            ctk.CTkLabel(inner, text=label, text_color=MUTED, font=ctk.CTkFont(size=12),
                         width=70, anchor="e").grid(row=r, column=0, sticky="e", padx=(0,6), pady=4)
            var = tk.StringVar(value=default)
            ctk.CTkEntry(inner, textvariable=var, fg_color=SURFACE2, border_color=BORDER,
                         text_color=TEXT, height=30).grid(row=r, column=1, sticky="ew", pady=4)
            form[key] = var

        ctk.CTkLabel(inner, text="Body", text_color=MUTED, font=ctk.CTkFont(size=12),
                     width=70, anchor="ne").grid(row=2, column=0, sticky="ne", padx=(0,6), pady=4)
        tb = ctk.CTkTextbox(inner, fg_color=SURFACE2, border_color=BORDER, text_color=TEXT,
                             font=ctk.CTkFont(size=13), wrap="word")
        tb.insert("1.0", note.get("body",""))
        tb.grid(row=2, column=1, sticky="nsew", pady=4)
        form["body"] = tb

    def _add_note(self):
        sl = self._sl_var.get().strip()
        nd = self._date_var.get().strip()
        body = self._body_tb.get("1.0","end").strip()
        if not sl or not body:
            messagebox.showerror("Validation", "Session label and body are required."); return
        self.db.create_note({"session_label": sl, "note_date": nd, "body": body})
        self._body_tb.delete("1.0","end")
        self.refresh()

    def _save_edit(self, id: int, form: dict):
        sl = form["session_label"].get().strip()
        if not sl:
            messagebox.showerror("Validation", "Session label is required."); return
        data = {
            "session_label": sl,
            "note_date": form["note_date"].get().strip(),
            "body": form["body"].get("1.0","end").rstrip(),
        }
        self.db.update_note(id, data)
        self.refresh()
        updated = next((n for n in self._notes if n["id"] == id), None)
        if updated:
            self._show_detail(updated)

    def _delete(self, note: dict):
        if messagebox.askyesno("Delete", "Delete this note?"):
            self.db.delete_note(note["id"])
            self._selected = None
            self.refresh()
            self._show_placeholder()

    def _clear_all(self):
        notes = self.db.list_notes()
        n = len(notes)
        if n == 0:
            messagebox.showinfo("Clear All", "No notes to clear.")
            return
        if messagebox.askyesno("Clear All Notes",
                               f"Permanently delete all {n} note(s)? This cannot be undone."):
            self.db.clear_table("notes")
            self._selected = None
            self.refresh()
            self._show_placeholder()

    def _export(self):
        path = filedialog.asksaveasfilename(
            title="Export Notes CSV", defaultextension=".csv",
            filetypes=[("CSV","*.csv")], initialfile="notes.csv"
        )
        if path:
            with open(path,"w",newline="",encoding="utf-8") as f:
                f.write(self.db.export_csv("notes"))
            messagebox.showinfo("Export", f"Exported to:\n{path}")
