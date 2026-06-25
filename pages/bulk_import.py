"""Bulk CSV Import page — folder/file picker with auto-detection."""
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import threading

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

TABLE_LABELS = {
    "players":     "Players / Roster",
    "magic_items": "Magic Items",
    "bestiary":    "Bestiary",
    "mechanics":   "Mechanics",
    "campaigns":   "Campaigns",
    "notes":       "Session Notes",
    "shops":       "Shops",
    "party_items": "Party Loot",
}

TABLE_COLUMNS = {
    "players":     "player_name, character_name, ac, max_hp, initiative_mod, passive_perception, notes",
    "magic_items": "name, item_type, rarity, requires_attunement, attunement_requirement, description, mechanical_effect, charges, source_campaign, tags",
    "bestiary":    "name, ac, max_hp, initiative_mod, cr, statblock_md, tags",
    "mechanics":   "title, body_md, campaign, tags",
    "campaigns":   "title, body_md, tags",
    "notes":       "session_label, note_date, body",
    "shops":       "shop_name, item_name, price, quantity, notes",
    "party_items": "item_name, owner, quantity, notes",
}


class BulkImportPage(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._results: list[dict] = []
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(16,4))
        ctk.CTkLabel(hdr, text="Bulk CSV Import",
                     font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT
                     ).pack(anchor="w")
        ctk.CTkLabel(hdr, text="Select a folder or CSV files — tables are auto-detected from column headers or filename.",
                     text_color=MUTED, font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(2,0))

        # Drop zone / buttons
        zone = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=12,
                             border_color=BORDER, border_width=2)
        zone.grid(row=1, column=0, sticky="ew", padx=16, pady=8)
        zone.columnconfigure((0,1,2), weight=1)

        ctk.CTkLabel(zone, text="📂", font=ctk.CTkFont(size=36)
                     ).grid(row=0, column=0, columnspan=3, pady=(24,8))
        ctk.CTkLabel(zone, text="Choose a folder or individual CSV files to import",
                     text_color=MUTED, font=ctk.CTkFont(size=13)
                     ).grid(row=1, column=0, columnspan=3, pady=(0,16))

        ctk.CTkButton(zone, text="📁  Choose Folder", height=38, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=13),
                      command=self._pick_folder
                      ).grid(row=2, column=0, padx=(24,8), pady=(0,24), sticky="ew")
        ctk.CTkButton(zone, text="📄  Choose CSV Files", height=38, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=TEXT, font=ctk.CTkFont(size=13),
                      command=self._pick_files
                      ).grid(row=2, column=1, padx=8, pady=(0,24), sticky="ew")
        ctk.CTkButton(zone, text="⬇  Export Templates", height=38, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=13),
                      command=self._export_templates
                      ).grid(row=2, column=2, padx=(8,24), pady=(0,24), sticky="ew")

        self._status_lbl = ctk.CTkLabel(self, text="", text_color=MUTED,
                                         font=ctk.CTkFont(size=12))
        self._status_lbl.grid(row=1, column=0, sticky="se", padx=24, pady=4)

        # Results area
        self._results_frame = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                                      scrollbar_button_color=ACCENT)
        self._results_frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0,8))
        self._results_frame.columnconfigure(0, weight=1)

        # Column reference
        ref_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        ref_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0,16))
        ref_frame.columnconfigure(0, weight=1)

        ctk.CTkLabel(ref_frame, text="CSV Column Reference",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color=ACCENT, anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=12, pady=(8,4))

        for i, (table, label) in enumerate(TABLE_LABELS.items()):
            row = ctk.CTkFrame(ref_frame, fg_color="transparent")
            row.grid(row=i+1, column=0, sticky="ew", padx=12, pady=1)
            row.columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=label, text_color=TEXT, font=ctk.CTkFont(size=11),
                         width=140, anchor="w").grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(row, text=TABLE_COLUMNS[table], text_color=MUTED,
                         font=ctk.CTkFont(family="Courier New", size=10), anchor="w"
                         ).grid(row=0, column=1, sticky="ew", padx=(8,0))

        ctk.CTkLabel(ref_frame, text="Tags: semicolon-separated  e.g.  Combat;Fire;Legendary",
                     text_color=MUTED, font=ctk.CTkFont(size=10)
                     ).grid(row=len(TABLE_LABELS)+1, column=0, sticky="w", padx=12, pady=(2,8))

    # ── Import logic ───────────────────────────────────────────────────────────

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="Select Folder Containing CSV Files")
        if not folder:
            return
        paths = [
            os.path.join(folder, f)
            for f in sorted(os.listdir(folder))
            if f.lower().endswith(".csv")
        ]
        if not paths:
            messagebox.showinfo("No CSVs", f"No .csv files found in:\n{folder}"); return
        self._run_import(paths)

    def _pick_files(self):
        paths = filedialog.askopenfilenames(
            title="Select CSV Files",
            filetypes=[("CSV files","*.csv"), ("All files","*.*")]
        )
        if paths:
            self._run_import(list(paths))

    def _run_import(self, paths: list[str]):
        self._status_lbl.configure(text=f"Importing {len(paths)} file(s)…")
        for w in self._results_frame.winfo_children():
            w.destroy()

        def worker():
            results = []
            for path in paths:
                filename = os.path.basename(path)
                try:
                    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                        text = f.read()
                    result = self.db.import_csv(filename, text)
                    result["filename"] = filename
                    result["path"] = path
                except Exception as e:
                    result = {
                        "filename": filename, "path": path,
                        "table": "unknown", "inserted": 0, "skipped": 0,
                        "errors": [str(e)],
                    }
                results.append(result)
            self.after(0, lambda: self._show_results(results))

        threading.Thread(target=worker, daemon=True).start()

    def _show_results(self, results: list[dict]):
        self._results = results
        for w in self._results_frame.winfo_children():
            w.destroy()

        total_inserted = sum(r.get("inserted", 0) for r in results)
        ok_count = sum(1 for r in results if r.get("table") != "unknown" and not r.get("errors"))
        err_count = sum(1 for r in results if r.get("table") == "unknown" or r.get("errors"))

        self._status_lbl.configure(
            text=f"{len(results)} file(s) · {total_inserted} rows inserted · {ok_count} ok · {err_count} errors"
        )

        # Summary bar
        summary = ctk.CTkFrame(self._results_frame, fg_color=SURFACE, corner_radius=6)
        summary.pack(fill="x", padx=4, pady=(0,8))
        ctk.CTkLabel(summary, text=f"Processed {len(results)} file(s)",
                     text_color=TEXT, font=ctk.CTkFont(size=13)
                     ).pack(side="left", padx=12, pady=8)
        ctk.CTkLabel(summary, text=f"{total_inserted} rows inserted",
                     text_color=SUCCESS, font=ctk.CTkFont(size=13)
                     ).pack(side="left", padx=8)
        if err_count:
            ctk.CTkLabel(summary, text=f"{err_count} errors",
                         text_color=DANGER, font=ctk.CTkFont(size=13)
                         ).pack(side="left", padx=8)
        ctk.CTkButton(summary, text="Clear", width=64, height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=lambda: [w.destroy() for w in self._results_frame.winfo_children()]
                      ).pack(side="right", padx=8)

        for res in results:
            is_ok = res.get("table") != "unknown" and not res.get("errors")
            border = SUCCESS if is_ok else DANGER
            card = ctk.CTkFrame(self._results_frame, fg_color=SURFACE, corner_radius=6,
                                 border_color=border, border_width=2)
            card.pack(fill="x", padx=4, pady=3)
            card.columnconfigure(1, weight=1)

            icon = "✓" if is_ok else ("?" if res.get("table") == "unknown" else "✕")
            icon_color = SUCCESS if is_ok else (MUTED if res.get("table") == "unknown" else DANGER)

            ctk.CTkLabel(card, text=icon, text_color=icon_color,
                         font=ctk.CTkFont(size=16, weight="bold"), width=32
                         ).grid(row=0, column=0, padx=(10,0), pady=10)

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.grid(row=0, column=1, sticky="ew", padx=8, pady=8)

            ctk.CTkLabel(info, text=res["filename"], text_color=TEXT,
                         font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
                         ).pack(anchor="w")

            if res.get("table") == "unknown":
                ctk.CTkLabel(info, text="Could not detect table — check headers or rename file",
                             text_color=DANGER, font=ctk.CTkFont(size=11), anchor="w"
                             ).pack(anchor="w")
            else:
                label = TABLE_LABELS.get(res["table"], res["table"])
                detail = f"→ {label} · {res.get('inserted',0)} inserted"
                if res.get("skipped"):
                    detail += f" · {res['skipped']} skipped"
                ctk.CTkLabel(info, text=detail, text_color=MUTED,
                             font=ctk.CTkFont(size=11), anchor="w").pack(anchor="w")

            if res.get("errors"):
                err_frame = ctk.CTkFrame(card, fg_color=SURFACE2, corner_radius=4)
                err_frame.grid(row=1, column=0, columnspan=2, sticky="ew",
                               padx=10, pady=(0,8))
                for err in res["errors"][:5]:
                    ctk.CTkLabel(err_frame, text=err, text_color=DANGER,
                                 font=ctk.CTkFont(size=11), anchor="w"
                                 ).pack(anchor="w", padx=8, pady=1)
                if len(res["errors"]) > 5:
                    ctk.CTkLabel(err_frame, text=f"…and {len(res['errors'])-5} more",
                                 text_color=MUTED, font=ctk.CTkFont(size=11), anchor="w"
                                 ).pack(anchor="w", padx=8, pady=(0,4))

    def _export_templates(self):
        folder = filedialog.askdirectory(title="Select Folder to Save Templates")
        if not folder:
            return
        for table, cols in TABLE_COLUMNS.items():
            path = os.path.join(folder, f"{table}_template.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write(cols.replace(", ", ",") + "\n")
        messagebox.showinfo("Templates Exported",
                            f"Blank template CSVs saved to:\n{folder}")

    def refresh(self):
        pass  # no auto-refresh needed
