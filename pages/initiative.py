"""Initiative Tracker page."""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import dice as dice_module

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
TURN_HL  = "#2a2038"  # highlight color for active turn

CONDITIONS = [
    "Blinded","Charmed","Deafened","Exhaustion","Frightened","Grappled",
    "Incapacitated","Invisible","Paralyzed","Petrified","Poisoned",
    "Prone","Restrained","Stunned","Unconscious",
]


class InitiativePage(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG)
        self.db = db
        self._combatants: list[dict] = []
        self._turn_idx: int = 0
        self._round: int = 1
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(1, weight=1)

        # ── Top bar ────────────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8, height=56)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16,4))
        top.grid_propagate(False)

        ctk.CTkLabel(top, text="⚔ Initiative Tracker",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT
                     ).pack(side="left", padx=16)

        self._round_lbl = ctk.CTkLabel(top, text="Round 1",
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        text_color=ACCENT)
        self._round_lbl.pack(side="left", padx=16)

        self._turn_lbl = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=13), text_color=MUTED)
        self._turn_lbl.pack(side="left", padx=8)

        ctk.CTkButton(top, text="▶ Next Turn", width=110, height=36, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=13),
                      command=self._next_turn).pack(side="right", padx=8)
        ctk.CTkButton(top, text="Reset", width=80, height=36, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=self._reset).pack(side="right")
        ctk.CTkButton(top, text="Save", width=72, height=36, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=self._save_encounter).pack(side="right", padx=(8,4))
        ctk.CTkButton(top, text="Load", width=72, height=36, fg_color=SURFACE2,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=12),
                      command=self._load_encounter).pack(side="right")

        # ── Main combatant list ────────────────────────────────────────────────
        self._list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                                   scrollbar_button_color=ACCENT)
        self._list_frame.grid(row=1, column=0, sticky="nsew", padx=(16,4), pady=(4,16))
        self._list_frame.columnconfigure(0, weight=1)

        # ── Right panel (add combatants) ───────────────────────────────────────
        right = ctk.CTkFrame(self, width=280, fg_color=SURFACE, corner_radius=8)
        right.grid(row=1, column=1, sticky="nsew", padx=(4,16), pady=(4,16))
        right.grid_propagate(False)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)

        ctk.CTkLabel(right, text="Add Combatants", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w", padx=12, pady=(12,8))

        # Add custom combatant
        custom = ctk.CTkFrame(right, fg_color=SURFACE2, corner_radius=6)
        custom.grid(row=1, column=0, sticky="ew", padx=8, pady=(0,8))
        custom.columnconfigure(0, weight=1)

        ctk.CTkLabel(custom, text="Custom", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=ACCENT).grid(row=0, column=0, columnspan=2, sticky="w",
                                              padx=8, pady=(8,4))

        fields = [("Name", "_cn_name", ""), ("AC", "_cn_ac", "10"),
                  ("Max HP", "_cn_hp", "10"), ("Init Mod", "_cn_init", "0"),
                  ("Initiative", "_cn_roll", "")]
        for i, (label, attr, default) in enumerate(fields):
            ctk.CTkLabel(custom, text=label, text_color=MUTED, font=ctk.CTkFont(size=11),
                         width=70, anchor="e").grid(row=i+1, column=0, sticky="e",
                                                     padx=(8,4), pady=2)
            var = tk.StringVar(value=default)
            setattr(self, attr+"_var", var)
            ctk.CTkEntry(custom, textvariable=var, fg_color=SURFACE, border_color=BORDER,
                         text_color=TEXT, height=26).grid(row=i+1, column=1, sticky="ew",
                                                           padx=(0,8), pady=2)

        btn_row = ctk.CTkFrame(custom, fg_color="transparent")
        btn_row.grid(row=len(fields)+1, column=0, columnspan=2, sticky="ew",
                     padx=8, pady=(4,8))
        ctk.CTkButton(btn_row, text="Roll Init", width=80, height=28, fg_color=SURFACE,
                      hover_color=BORDER, text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=self._roll_custom_init).pack(side="left")
        ctk.CTkButton(btn_row, text="Add", width=64, height=28, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._add_custom).pack(side="right")

        # Load players from DB
        ctk.CTkButton(right, text="Load Players from Roster", height=30,
                      fg_color=SURFACE2, hover_color=BORDER, text_color=MUTED,
                      font=ctk.CTkFont(size=12), corner_radius=6,
                      command=self._load_players).grid(row=2, column=0, sticky="ew",
                                                       padx=8, pady=(0,8))

        # Bestiary list
        ctk.CTkLabel(right, text="Bestiary", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT).grid(row=3, column=0, sticky="nw", padx=12, pady=(4,4))
        self._beast_search_var = tk.StringVar()
        self._beast_search_var.trace_add("write", lambda *_: self._refresh_bestiary())
        ctk.CTkEntry(right, textvariable=self._beast_search_var, placeholder_text="Search bestiary…",
                     fg_color=SURFACE2, border_color=BORDER, text_color=TEXT, height=28
                     ).grid(row=4, column=0, sticky="ew", padx=8, pady=(0,4))

        self._beast_frame = ctk.CTkScrollableFrame(right, fg_color="transparent",
                                                    scrollbar_button_color=ACCENT)
        self._beast_frame.grid(row=5, column=0, sticky="nsew", padx=4, pady=(0,8))
        right.rowconfigure(5, weight=1)

        # Dice roller
        dice_f = ctk.CTkFrame(right, fg_color=SURFACE2, corner_radius=6)
        dice_f.grid(row=6, column=0, sticky="ew", padx=8, pady=(0,12))
        dice_f.columnconfigure(0, weight=1)
        ctk.CTkLabel(dice_f, text="Dice Roller", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=ACCENT).grid(row=0, column=0, columnspan=2, sticky="w",
                                              padx=8, pady=(6,2))
        self._dice_var = tk.StringVar(value="1d20")
        ctk.CTkEntry(dice_f, textvariable=self._dice_var, fg_color=SURFACE,
                     border_color=BORDER, text_color=TEXT, height=26
                     ).grid(row=1, column=0, sticky="ew", padx=(8,4), pady=(0,4))
        ctk.CTkButton(dice_f, text="Roll", width=50, height=26, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                      command=self._roll_dice).grid(row=1, column=1, padx=(0,8))
        self._dice_result = ctk.CTkLabel(dice_f, text="", text_color=TEXT,
                                          font=ctk.CTkFont(size=12), wraplength=200)
        self._dice_result.grid(row=2, column=0, columnspan=2, sticky="w", padx=8, pady=(0,6))

    # ── Combatant list rendering ───────────────────────────────────────────────

    def _render_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

        # Sort by initiative descending
        self._combatants.sort(key=lambda c: -int(c.get("initiative", 0)))

        for i, c in enumerate(self._combatants):
            is_active = (i == self._turn_idx % max(len(self._combatants), 1))
            self._render_combatant_row(c, i, is_active)

        # Persist to the shared live encounter so the DM Shield panel stays in sync.
        self._persist_live()

    def _persist_live(self):
        try:
            self.db.set_live_encounter({
                "combatants": self._combatants,
                "turn_idx": self._turn_idx,
                "round": self._round,
            })
        except Exception:
            pass

    def _load_live(self):
        state = self.db.get_live_encounter()
        self._combatants = state.get("combatants", []) or []
        self._turn_idx = state.get("turn_idx", 0)
        self._round = state.get("round", 1)
        self._round_lbl.configure(text=f"Round {self._round}")
        if self._combatants:
            active = self._combatants[self._turn_idx % len(self._combatants)]
            self._turn_lbl.configure(text=f"→ {active['name']}")
        else:
            self._turn_lbl.configure(text="")

    def _render_combatant_row(self, c: dict, idx: int, active: bool):
        bg = TURN_HL if active else SURFACE2
        border = ACCENT if active else BORDER

        outer = ctk.CTkFrame(self._list_frame, fg_color=bg, corner_radius=6,
                              border_color=border, border_width=1 if active else 0)
        outer.pack(fill="x", padx=4, pady=3)
        outer.columnconfigure(2, weight=1)

        # Turn indicator
        ctk.CTkLabel(outer, text="▶" if active else "  ", text_color=ACCENT,
                     font=ctk.CTkFont(size=13), width=20
                     ).grid(row=0, column=0, padx=(8,0), pady=8)

        # Initiative badge
        ctk.CTkLabel(outer, text=str(c.get("initiative","?")),
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=ACCENT, width=40
                     ).grid(row=0, column=1, padx=4)

        # Name + conditions
        name_f = ctk.CTkFrame(outer, fg_color="transparent")
        name_f.grid(row=0, column=2, sticky="ew", padx=4)
        ctk.CTkLabel(name_f, text=c["name"], anchor="w", text_color=TEXT,
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        if c.get("conditions"):
            ctk.CTkLabel(name_f, text="  ".join(c["conditions"]), anchor="w",
                         text_color="#e74c3c", font=ctk.CTkFont(size=11)).pack(anchor="w")

        # HP bar + controls
        hp_f = ctk.CTkFrame(outer, fg_color="transparent")
        hp_f.grid(row=0, column=3, padx=8)

        cur_hp = c.get("current_hp", c.get("max_hp", 0))
        max_hp = c.get("max_hp", 1)
        hp_pct = max(0, min(1, cur_hp / max(max_hp, 1)))
        hp_color = SUCCESS if hp_pct > 0.5 else ("#f39c12" if hp_pct > 0.25 else DANGER)

        ctk.CTkLabel(hp_f, text=f"{cur_hp}/{max_hp} HP",
                     text_color=hp_color, font=ctk.CTkFont(size=12, weight="bold")
                     ).grid(row=0, column=0, columnspan=3, pady=(0,2))

        ctk.CTkButton(hp_f, text="−", width=28, height=24, fg_color=DANGER,
                      hover_color="#e74c3c", text_color=TEXT, font=ctk.CTkFont(size=14),
                      command=lambda c=c: self._damage_dialog(c)
                      ).grid(row=1, column=0)
        ctk.CTkButton(hp_f, text="+", width=28, height=24, fg_color=SUCCESS,
                      hover_color="#2ecc71", text_color=TEXT, font=ctk.CTkFont(size=14),
                      command=lambda c=c: self._heal_dialog(c)
                      ).grid(row=1, column=1, padx=2)

        ctk.CTkLabel(hp_f, text=f"AC {c.get('ac','?')}",
                     text_color=MUTED, font=ctk.CTkFont(size=11)
                     ).grid(row=1, column=2, padx=(4,0))

        # Conditions + remove buttons
        btn_f = ctk.CTkFrame(outer, fg_color="transparent")
        btn_f.grid(row=0, column=4, padx=(0,4))

        ctk.CTkButton(btn_f, text="☠", width=28, height=24, fg_color="transparent",
                      hover_color=SURFACE, text_color=MUTED, font=ctk.CTkFont(size=13),
                      command=lambda c=c: self._conditions_dialog(c)
                      ).pack()
        ctk.CTkButton(btn_f, text="✕", width=28, height=24, fg_color="transparent",
                      hover_color=DANGER, text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=lambda c=c, i=idx: self._remove_combatant(i)
                      ).pack(pady=(2,0))

    # ── Actions ────────────────────────────────────────────────────────────────

    def _next_turn(self):
        if not self._combatants:
            return
        self._turn_idx += 1
        if self._turn_idx >= len(self._combatants):
            self._turn_idx = 0
            self._round += 1
            self._round_lbl.configure(text=f"Round {self._round}")

        active = self._combatants[self._turn_idx % len(self._combatants)]
        self._turn_lbl.configure(text=f"→ {active['name']}")
        self._render_list()

    def _reset(self):
        if self._combatants and not messagebox.askyesno("Reset", "Clear all combatants and reset round?"):
            return
        self._combatants.clear()
        self._turn_idx = 0
        self._round = 1
        self._round_lbl.configure(text="Round 1")
        self._turn_lbl.configure(text="")
        self._render_list()

    def _remove_combatant(self, idx: int):
        if 0 <= idx < len(self._combatants):
            del self._combatants[idx]
            if self._turn_idx >= len(self._combatants):
                self._turn_idx = max(0, len(self._combatants) - 1)
            self._render_list()

    def _damage_dialog(self, c: dict):
        val = simpledialog.askinteger("Damage", f"Damage to {c['name']}:", minvalue=0, parent=self)
        if val is not None:
            c["current_hp"] = max(0, c.get("current_hp", c.get("max_hp", 0)) - val)
            self._render_list()

    def _heal_dialog(self, c: dict):
        val = simpledialog.askinteger("Heal", f"Heal {c['name']}:", minvalue=0, parent=self)
        if val is not None:
            c["current_hp"] = min(c.get("max_hp", 999),
                                  c.get("current_hp", c.get("max_hp", 0)) + val)
            self._render_list()

    def _conditions_dialog(self, c: dict):
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Conditions — {c['name']}")
        dlg.geometry("300x420")
        dlg.configure(fg_color=SURFACE)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Toggle Conditions", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).pack(pady=(16,8))

        current = set(c.get("conditions", []))
        vars_: dict[str, tk.BooleanVar] = {}
        for cond in (self.db.condition_names() or CONDITIONS):
            v = tk.BooleanVar(value=cond in current)
            ctk.CTkCheckBox(dlg, text=cond, variable=v, text_color=TEXT,
                            checkbox_width=18, checkbox_height=18,
                            fg_color=DANGER, hover_color="#e74c3c", border_color=BORDER
                            ).pack(anchor="w", padx=16, pady=2)
            vars_[cond] = v

        def apply():
            c["conditions"] = [cond for cond, v in vars_.items() if v.get()]
            self._render_list()
            dlg.destroy()

        ctk.CTkButton(dlg, text="Apply", fg_color=ACCENT, hover_color=ACCENT_H,
                      text_color=TEXT, font=ctk.CTkFont(size=13), height=36,
                      command=apply).pack(fill="x", padx=16, pady=16)

    def _add_custom(self):
        name = self._cn_name_var.get().strip()
        if not name:
            messagebox.showerror("Validation", "Name is required."); return
        try:
            ac = int(self._cn_ac_var.get() or 10)
            max_hp = int(self._cn_hp_var.get() or 10)
            init_mod = int(self._cn_init_var.get() or 0)
            roll_str = self._cn_roll_var.get().strip()
            initiative = int(roll_str) if roll_str else dice_module.roll(f"1d20{'+'+str(init_mod) if init_mod >= 0 else str(init_mod)}")["total"]
        except (ValueError, TypeError):
            messagebox.showerror("Validation", "AC, HP, and modifiers must be numbers."); return

        self._combatants.append({
            "name": name, "ac": ac, "max_hp": max_hp,
            "current_hp": max_hp, "initiative_mod": init_mod,
            "initiative": initiative, "conditions": [], "is_player": False,
        })
        self._cn_name_var.set("")
        self._cn_roll_var.set("")
        self._render_list()

    def _roll_custom_init(self):
        try:
            mod = int(self._cn_init_var.get() or 0)
        except ValueError:
            mod = 0
        expr = f"1d20+{mod}" if mod >= 0 else f"1d20{mod}"
        result = dice_module.roll(expr)
        self._cn_roll_var.set(str(result["total"]))

    def _load_players(self):
        players = self.db.list_players()
        existing_names = {c["name"] for c in self._combatants}
        added = 0
        for p in players:
            if p["character_name"] in existing_names:
                continue
            mod = p.get("initiative_mod", 0)
            expr = f"1d20+{mod}" if mod >= 0 else f"1d20{mod}"
            roll = dice_module.roll(expr)
            self._combatants.append({
                "name": p["character_name"], "ac": p.get("ac", 10),
                "max_hp": p.get("max_hp", 10), "current_hp": p.get("max_hp", 10),
                "initiative_mod": mod, "initiative": roll["total"],
                "conditions": [], "is_player": True,
            })
            added += 1
        if added == 0:
            messagebox.showinfo("Roster", "No new players to add (empty roster or already added).")
        self._render_list()

    def _refresh_bestiary(self):
        search = self._beast_search_var.get().strip()
        entries = self.db.list_bestiary(search=search)
        for w in self._beast_frame.winfo_children():
            w.destroy()
        for e in entries[:50]:  # cap at 50 for perf
            row = ctk.CTkFrame(self._beast_frame, fg_color="transparent")
            row.pack(fill="x", padx=2, pady=1)
            row.columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=f"{e['name']} (CR {e.get('cr','?')})",
                         anchor="w", text_color=TEXT, font=ctk.CTkFont(size=12)
                         ).grid(row=0, column=0, sticky="ew", padx=4)
            ctk.CTkButton(row, text="+", width=24, height=24, fg_color=ACCENT,
                          hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                          command=lambda e=e: self._add_from_bestiary(e)
                          ).grid(row=0, column=1, padx=(0,2))

    def _add_from_bestiary(self, entry: dict):
        mod = entry.get("initiative_mod", 0)
        expr = f"1d20+{mod}" if mod >= 0 else f"1d20{mod}"
        roll = dice_module.roll(expr)

        # Ask for a custom name/count
        name = simpledialog.askstring(
            "Add to Initiative",
            f"Name for this {entry['name']}:\n(e.g. 'Goblin 1' for multiple)",
            initialvalue=entry["name"], parent=self
        )
        if not name:
            return

        self._combatants.append({
            "name": name, "ac": entry.get("ac", 10),
            "max_hp": entry.get("max_hp", 10), "current_hp": entry.get("max_hp", 10),
            "initiative_mod": mod, "initiative": roll["total"],
            "conditions": [], "is_player": False, "cr": entry.get("cr","0"),
        })
        self._render_list()

    def _roll_dice(self):
        expr = self._dice_var.get().strip()
        if not expr:
            return
        result = dice_module.roll(expr)
        self._dice_result.configure(text=dice_module.format_result(result))

    # ── Save / Load encounter ──────────────────────────────────────────────────

    def _save_encounter(self):
        name = simpledialog.askstring("Save Encounter", "Encounter name:", parent=self)
        if not name:
            return
        state = {
            "combatants": self._combatants,
            "turn_idx": self._turn_idx,
            "round": self._round,
        }
        self.db.save_encounter(name, json.dumps(state))
        messagebox.showinfo("Saved", f"Encounter '{name}' saved.")

    def _load_encounter(self):
        encounters = self.db.list_saved_encounters()
        if not encounters:
            messagebox.showinfo("Load", "No saved encounters."); return

        dlg = ctk.CTkToplevel(self)
        dlg.title("Load Encounter")
        dlg.geometry("360x400")
        dlg.configure(fg_color=SURFACE)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Select Encounter",
                     font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT
                     ).pack(pady=(16,8))

        listbox = ctk.CTkScrollableFrame(dlg, fg_color=SURFACE2)
        listbox.pack(fill="both", expand=True, padx=12, pady=(0,8))
        listbox.columnconfigure(0, weight=1)

        selected: list[dict] = [None]

        def select(enc):
            selected[0] = enc
            for w in listbox.winfo_children():
                if hasattr(w, "_is_enc_row"):
                    w.configure(fg_color=SURFACE2)
            # highlight selected (find by id)

        for enc in encounters:
            row = ctk.CTkFrame(listbox, fg_color=SURFACE2, cursor="hand2", corner_radius=4)
            row._is_enc_row = True
            row.pack(fill="x", padx=4, pady=2)
            row.columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=enc["name"], text_color=TEXT, font=ctk.CTkFont(size=13),
                         anchor="w").grid(row=0, column=0, sticky="ew", padx=8, pady=6)
            ctk.CTkLabel(row, text=enc.get("updated_at",""), text_color=MUTED,
                         font=ctk.CTkFont(size=10)).grid(row=1, column=0, sticky="w", padx=8)

            load_enc = enc  # capture
            row.bind("<Button-1>", lambda e, enc=load_enc: select(enc))
            for c in row.winfo_children():
                c.bind("<Button-1>", lambda e, enc=load_enc: select(enc))

            def do_load(enc=enc):
                self._do_load_encounter(enc)
                dlg.destroy()

            ctk.CTkButton(row, text="Load", width=56, height=26, fg_color=ACCENT,
                          hover_color=ACCENT_H, text_color=TEXT, font=ctk.CTkFont(size=12),
                          command=do_load).grid(row=0, column=1, rowspan=2, padx=(0,8))

        ctk.CTkButton(dlg, text="Close", height=36, fg_color=SURFACE2, hover_color=BORDER,
                      text_color=MUTED, command=dlg.destroy).pack(fill="x", padx=12, pady=(0,12))

    def _do_load_encounter(self, enc: dict):
        try:
            state = json.loads(enc["state_json"])
            self._combatants = state.get("combatants", [])
            self._turn_idx = state.get("turn_idx", 0)
            self._round = state.get("round", 1)
            self._round_lbl.configure(text=f"Round {self._round}")
            if self._combatants:
                active = self._combatants[self._turn_idx % len(self._combatants)]
                self._turn_lbl.configure(text=f"→ {active['name']}")
            self._render_list()
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def refresh(self):
        # Pull the shared live encounter (may have changed in the DM Shield panel).
        self._load_live()
        self._refresh_bestiary()
        self._render_list()
