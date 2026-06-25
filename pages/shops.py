"""Shops & Loot page — three tabs: Shops, Party Loot, Party Roster."""
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


class ShopsPage(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Tab bar
        tab_bar = ctk.CTkFrame(self, fg_color=SURFACE, height=42, corner_radius=8)
        tab_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16,4))

        self._tab_btns: list[ctk.CTkButton] = []
        self._tabs: list[ctk.CTkFrame] = []
        self._active_tab = 0

        for i, label in enumerate(["⚖  Shops", "🎒  Party Loot", "🧙  Party Roster"]):
            btn = ctk.CTkButton(tab_bar, text=label, height=34, fg_color="transparent",
                                hover_color=SURFACE2, text_color=MUTED,
                                font=ctk.CTkFont(size=13), corner_radius=6,
                                command=lambda i=i: self._switch_tab(i))
            btn.pack(side="left", padx=(4,0), pady=4)
            self._tab_btns.append(btn)

        # Content frames
        self._tab_shops   = _ShopsTab(self, self.db)
        self._tab_loot    = _LootTab(self, self.db)
        self._tab_roster  = _RosterTab(self, self.db)

        for t in [self._tab_shops, self._tab_loot, self._tab_roster]:
            t.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0,16))
            t.grid_remove()

        self._switch_tab(0)

    def _switch_tab(self, i: int):
        tabs = [self._tab_shops, self._tab_loot, self._tab_roster]
        for j, (btn, tab) in enumerate(zip(self._tab_btns, tabs)):
            if j == i:
                btn.configure(fg_color=ACCENT, text_color=TEXT)
                tab.grid()
                tab.refresh()
            else:
                btn.configure(fg_color="transparent", text_color=MUTED)
                tab.grid_remove()
        self._active_tab = i

    def refresh(self):
        tabs = [self._tab_shops, self._tab_loot, self._tab_roster]
        tabs[self._active_tab].refresh()


# ── Shops tab ──────────────────────────────────────────────────────────────────

class _ShopsTab(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._items: list[dict] = []
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Add form
        form_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        form_frame.grid(row=0, column=0, sticky="ew", pady=(0,8))
        form_frame.columnconfigure((1,3,5,7,9), weight=1)

        ctk.CTkLabel(form_frame, text="Shop", text_color=MUTED, font=ctk.CTkFont(size=12)
                     ).grid(row=0, column=0, padx=(12,4), pady=10)
        self._shop_var = tk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self._shop_var, fg_color=SURFACE2,
                     border_color=BORDER, text_color=TEXT, height=30
                     ).grid(row=0, column=1, sticky="ew", padx=(0,8), pady=10)

        ctk.CTkLabel(form_frame, text="Item", text_color=MUTED, font=ctk.CTkFont(size=12)
                     ).grid(row=0, column=2, padx=(0,4))
        self._item_var = tk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self._item_var, fg_color=SURFACE2,
                     border_color=BORDER, text_color=TEXT, height=30
                     ).grid(row=0, column=3, sticky="ew", padx=(0,8))

        ctk.CTkLabel(form_frame, text="Price", text_color=MUTED, font=ctk.CTkFont(size=12)
                     ).grid(row=0, column=4, padx=(0,4))
        self._price_var = tk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self._price_var, fg_color=SURFACE2,
                     border_color=BORDER, text_color=TEXT, height=30, width=80
                     ).grid(row=0, column=5, sticky="ew", padx=(0,8))

        ctk.CTkLabel(form_frame, text="Qty", text_color=MUTED, font=ctk.CTkFont(size=12)
                     ).grid(row=0, column=6, padx=(0,4))
        self._qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(form_frame, textvariable=self._qty_var, fg_color=SURFACE2,
                     border_color=BORDER, text_color=TEXT, height=30, width=50
                     ).grid(row=0, column=7, sticky="ew", padx=(0,8))

        ctk.CTkLabel(form_frame, text="Notes", text_color=MUTED, font=ctk.CTkFont(size=12)
                     ).grid(row=0, column=8, padx=(0,4))
        self._notes_var = tk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self._notes_var, fg_color=SURFACE2,
                     border_color=BORDER, text_color=TEXT, height=30
                     ).grid(row=0, column=9, sticky="ew", padx=(0,8))

        ctk.CTkButton(form_frame, text="Add", width=60, height=30, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._add).grid(row=0, column=10, padx=(0,12))

        # Table header
        header = ctk.CTkFrame(self, fg_color=SURFACE2, height=30, corner_radius=4)
        header.grid(row=1, column=0, sticky="new")
        for col, (label, w) in enumerate([
            ("Shop", 160), ("Item", 200), ("Price", 80), ("Qty", 50), ("Notes", 100), ("", 70)
        ]):
            ctk.CTkLabel(header, text=label, text_color=MUTED,
                         font=ctk.CTkFont(size=11), anchor="w", width=w
                         ).pack(side="left" if col < 5 else "right", padx=(8 if col==0 else 4,4))

        # Rows
        self._rows_frame = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                                   scrollbar_button_color=ACCENT)
        self._rows_frame.grid(row=2, column=0, sticky="nsew")
        self.grid_rowconfigure(2, weight=1)

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", pady=(4,0))
        ctk.CTkButton(footer, text="Export CSV", height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=self._export).pack(side="right", padx=4)

    def _render(self):
        for w in self._rows_frame.winfo_children():
            w.destroy()

        # Group by shop
        shops: dict[str, list[dict]] = {}
        for it in self._items:
            shops.setdefault(it["shop_name"], []).append(it)

        for shop_name, items in shops.items():
            ctk.CTkLabel(self._rows_frame, text=shop_name,
                         font=ctk.CTkFont(size=12, weight="bold"), text_color=ACCENT, anchor="w"
                         ).pack(fill="x", padx=8, pady=(8,2))
            for it in items:
                row = ctk.CTkFrame(self._rows_frame, fg_color=SURFACE2, corner_radius=4)
                row.pack(fill="x", padx=4, pady=2)
                row.columnconfigure(1, weight=1)
                ctk.CTkLabel(row, text=it["item_name"], anchor="w", text_color=TEXT,
                             font=ctk.CTkFont(size=12), width=200
                             ).grid(row=0, column=0, padx=(8,4), pady=6, sticky="w")
                ctk.CTkLabel(row, text=str(it.get("price","")), anchor="w", text_color=MUTED,
                             font=ctk.CTkFont(size=12), width=80
                             ).grid(row=0, column=1, padx=4)
                ctk.CTkLabel(row, text=f"×{it.get('quantity',1)}", anchor="w", text_color=MUTED,
                             font=ctk.CTkFont(size=12), width=40
                             ).grid(row=0, column=2, padx=4)
                if it.get("notes"):
                    ctk.CTkLabel(row, text=it["notes"], anchor="w", text_color=MUTED,
                                 font=ctk.CTkFont(size=11)
                                 ).grid(row=0, column=3, padx=4, sticky="ew")
                row.columnconfigure(3, weight=1)
                ctk.CTkButton(row, text="✕", width=28, height=24, fg_color="transparent",
                              hover_color=DANGER, text_color=MUTED, font=ctk.CTkFont(size=11),
                              command=lambda it=it: self._delete(it)
                              ).grid(row=0, column=4, padx=(0,8))

    def refresh(self):
        self._items = self.db.list_shop_items()
        self._render()

    def _add(self):
        shop = self._shop_var.get().strip()
        item = self._item_var.get().strip()
        if not shop or not item:
            messagebox.showerror("Validation", "Shop and Item name are required."); return
        self.db.create_shop_item({
            "shop_name": shop, "item_name": item,
            "price": self._price_var.get().strip(),
            "quantity": self._qty_var.get().strip() or "1",
            "notes": self._notes_var.get().strip() or None,
        })
        self._item_var.set(""); self._price_var.set(""); self._qty_var.set("1"); self._notes_var.set("")
        self.refresh()

    def _delete(self, it: dict):
        if messagebox.askyesno("Delete", f"Remove '{it['item_name']}' from {it['shop_name']}?"):
            self.db.delete_shop_item(it["id"])
            self.refresh()

    def _export(self):
        path = filedialog.asksaveasfilename(
            title="Export Shops CSV", defaultextension=".csv",
            filetypes=[("CSV","*.csv")], initialfile="shops.csv"
        )
        if path:
            with open(path,"w",newline="",encoding="utf-8") as f:
                f.write(self.db.export_csv("shops"))
            messagebox.showinfo("Export", f"Exported to:\n{path}")


# ── Party Loot tab ─────────────────────────────────────────────────────────────

class _LootTab(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._items: list[dict] = []
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        form_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        form_frame.grid(row=0, column=0, sticky="ew", pady=(0,8))
        form_frame.columnconfigure((1,3,5,7), weight=1)

        for col, (label, attr, default) in enumerate([
            ("Item", "_loot_item", ""), ("Owner", "_loot_owner", ""),
            ("Qty", "_loot_qty", "1"), ("Notes", "_loot_notes", ""),
        ]):
            ctk.CTkLabel(form_frame, text=label, text_color=MUTED, font=ctk.CTkFont(size=12)
                         ).grid(row=0, column=col*2, padx=(12 if col==0 else 4, 4), pady=10)
            var = tk.StringVar(value=default)
            setattr(self, attr+"_var", var)
            ctk.CTkEntry(form_frame, textvariable=var, fg_color=SURFACE2,
                         border_color=BORDER, text_color=TEXT, height=30
                         ).grid(row=0, column=col*2+1, sticky="ew", padx=(0,8))

        ctk.CTkButton(form_frame, text="Add", width=60, height=30, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._add).grid(row=0, column=8, padx=(0,12))

        self._rows_frame = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                                   scrollbar_button_color=ACCENT)
        self._rows_frame.grid(row=2, column=0, sticky="nsew")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", pady=(4,0))
        ctk.CTkButton(footer, text="Export CSV", height=28, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=self._export).pack(side="right", padx=4)

    def _render(self):
        for w in self._rows_frame.winfo_children():
            w.destroy()
        owners: dict[str, list[dict]] = {}
        for it in self._items:
            owners.setdefault(it.get("owner",""), []).append(it)
        for owner, items in owners.items():
            ctk.CTkLabel(self._rows_frame, text=owner or "Unassigned",
                         font=ctk.CTkFont(size=12, weight="bold"), text_color=ACCENT, anchor="w"
                         ).pack(fill="x", padx=8, pady=(8,2))
            for it in items:
                row = ctk.CTkFrame(self._rows_frame, fg_color=SURFACE2, corner_radius=4)
                row.pack(fill="x", padx=4, pady=2)
                row.columnconfigure(0, weight=1)
                ctk.CTkLabel(row, text=f"{it['item_name']} ×{it.get('quantity',1)}",
                             anchor="w", text_color=TEXT, font=ctk.CTkFont(size=12)
                             ).grid(row=0, column=0, padx=8, pady=6, sticky="w")
                if it.get("notes"):
                    ctk.CTkLabel(row, text=it["notes"], anchor="w", text_color=MUTED,
                                 font=ctk.CTkFont(size=11)).grid(row=0, column=1, padx=4)
                ctk.CTkButton(row, text="✕", width=28, height=24, fg_color="transparent",
                              hover_color=DANGER, text_color=MUTED, font=ctk.CTkFont(size=11),
                              command=lambda it=it: self._delete(it)
                              ).grid(row=0, column=2, padx=(0,8))

    def refresh(self):
        self._items = self.db.list_party_items()
        self._render()

    def _add(self):
        item = self._loot_item_var.get().strip()
        if not item:
            messagebox.showerror("Validation", "Item name is required."); return
        self.db.create_party_item({
            "item_name": item,
            "owner": self._loot_owner_var.get().strip() or "Party",
            "quantity": self._loot_qty_var.get().strip() or "1",
            "notes": self._loot_notes_var.get().strip() or None,
        })
        self._loot_item_var.set(""); self._loot_qty_var.set("1"); self._loot_notes_var.set("")
        self.refresh()

    def _delete(self, it: dict):
        if messagebox.askyesno("Delete", f"Remove '{it['item_name']}'?"):
            self.db.delete_party_item(it["id"])
            self.refresh()

    def _export(self):
        path = filedialog.asksaveasfilename(
            title="Export Party Loot CSV", defaultextension=".csv",
            filetypes=[("CSV","*.csv")], initialfile="party_items.csv"
        )
        if path:
            with open(path,"w",newline="",encoding="utf-8") as f:
                f.write(self.db.export_csv("party_items"))
            messagebox.showinfo("Export", f"Exported to:\n{path}")


# ── Party Roster tab ───────────────────────────────────────────────────────────

class _RosterTab(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._players: list[dict] = []
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0,8))
        ctk.CTkLabel(hdr, text="Player / Character Roster",
                     font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT, anchor="w"
                     ).pack(side="left")
        ctk.CTkButton(hdr, text="+ Add Player", height=30, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._add_dialog).pack(side="right")
        ctk.CTkButton(hdr, text="Export CSV", height=30, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=self._export).pack(side="right", padx=(0,8))

        self._table = ctk.CTkScrollableFrame(self, fg_color=SURFACE, corner_radius=8,
                                              scrollbar_button_color=ACCENT)
        self._table.grid(row=1, column=0, sticky="nsew")
        self._table.columnconfigure((0,1,2,3,4,5), weight=1)

        # Column headers
        for col, label in enumerate(["Player", "Character", "AC", "HP", "Init Mod", "Pass Perc"]):
            ctk.CTkLabel(self._table, text=label, text_color=MUTED,
                         font=ctk.CTkFont(size=11, weight="bold"), anchor="w"
                         ).grid(row=0, column=col, sticky="ew", padx=8, pady=(8,4))

    def _render(self):
        for w in self._table.winfo_children():
            w.destroy()
        for col, label in enumerate(["Player", "Character", "AC", "HP", "Init Mod", "Pass Perc", ""]):
            ctk.CTkLabel(self._table, text=label, text_color=MUTED,
                         font=ctk.CTkFont(size=11, weight="bold"), anchor="w"
                         ).grid(row=0, column=col, sticky="ew", padx=8, pady=(8,4))
        self._table.columnconfigure((0,1,2,3,4,5), weight=1)

        for r, p in enumerate(self._players, start=1):
            bg = SURFACE if r % 2 == 0 else SURFACE2
            for col, val in enumerate([
                p["player_name"], p["character_name"], p.get("ac",""),
                p.get("max_hp",""), p.get("initiative_mod",""), p.get("passive_perception","")
            ]):
                ctk.CTkLabel(self._table, text=str(val), text_color=TEXT,
                             font=ctk.CTkFont(size=12), anchor="w"
                             ).grid(row=r, column=col, sticky="ew", padx=8, pady=4)
            ctk.CTkButton(self._table, text="✕", width=28, height=24,
                          fg_color="transparent", hover_color=DANGER,
                          text_color=MUTED, font=ctk.CTkFont(size=11),
                          command=lambda p=p: self._delete(p)
                          ).grid(row=r, column=6, padx=(0,8))

    def refresh(self):
        self._players = self.db.list_players()
        self._render()

    def _add_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Add Player")
        dlg.geometry("420x360")
        dlg.configure(fg_color=SURFACE)
        dlg.grab_set()
        dlg.columnconfigure(1, weight=1)

        fields = [
            ("Player Name *", "player_name", ""),
            ("Character Name *", "character_name", ""),
            ("AC", "ac", "10"),
            ("Max HP", "max_hp", "10"),
            ("Initiative Mod", "initiative_mod", "0"),
            ("Passive Perception", "passive_perception", "10"),
        ]
        vars_: dict[str, tk.StringVar] = {}
        for r, (label, key, default) in enumerate(fields):
            ctk.CTkLabel(dlg, text=label, text_color=MUTED, font=ctk.CTkFont(size=12),
                         anchor="e").grid(row=r, column=0, sticky="e", padx=(12,6), pady=6)
            v = tk.StringVar(value=default)
            ctk.CTkEntry(dlg, textvariable=v, fg_color=SURFACE2, border_color=BORDER,
                         text_color=TEXT, height=30).grid(row=r, column=1, sticky="ew",
                                                           padx=(0,12), pady=6)
            vars_[key] = v

        def save():
            pn = vars_["player_name"].get().strip()
            cn = vars_["character_name"].get().strip()
            if not pn or not cn:
                messagebox.showerror("Validation", "Player name and character name are required.")
                return
            self.db.create_player({
                k: (int(v.get()) if k not in ("player_name","character_name") else v.get().strip())
                for k, v in vars_.items()
            })
            self.refresh()
            dlg.destroy()

        ctk.CTkButton(dlg, text="Save", fg_color=ACCENT, hover_color=ACCENT_H,
                      text_color=TEXT, font=ctk.CTkFont(size=13), height=36,
                      command=save).grid(row=len(fields), column=0, columnspan=2,
                                         padx=12, pady=(8,12), sticky="ew")

    def _delete(self, p: dict):
        if messagebox.askyesno("Delete", f"Remove {p['character_name']} from roster?"):
            self.db.delete_player(p["id"])
            self.refresh()

    def _export(self):
        path = filedialog.asksaveasfilename(
            title="Export Roster CSV", defaultextension=".csv",
            filetypes=[("CSV","*.csv")], initialfile="players.csv"
        )
        if path:
            with open(path,"w",newline="",encoding="utf-8") as f:
                f.write(self.db.export_csv("players"))
            messagebox.showinfo("Export", f"Exported to:\n{path}")
