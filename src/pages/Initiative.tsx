import { useEffect, useState, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  DndContext,
  DragEndEvent,
  useDraggable,
  useDroppable,
} from "@dnd-kit/core";

// ── Types ────────────────────────────────────────────────────────────────────

interface Player {
  id?: number;
  characterName: string;
  ac: number;
  maxHp: number;
  initiativeMod: number;
}

interface BestiaryEntry {
  id?: number;
  name: string;
  ac: number;
  maxHp: number;
  initiativeMod: number;
  cr: string;
}

interface Combatant {
  id: string;
  source: "player" | "monster" | "custom";
  displayName: string;
  ac: number;
  currentHp: number;
  maxHp: number;
  initiativeRoll: number;
  initiativeMod: number;
  conditions: string[];
  isCurrentTurn: boolean;
}

interface SavedEncounter {
  id?: number;
  name: string;
  stateJson: string;
  updatedAt?: string;
}

interface RollResult {
  total: number;
  keptRolls: number[];
  allRolls: number[];
  modifier: number;
  expr: string;
}

// ── Constants ────────────────────────────────────────────────────────────────

const CONDITIONS = [
  "Blinded", "Charmed", "Deafened", "Exhaustion", "Frightened",
  "Grappled", "Incapacitated", "Invisible", "Paralyzed", "Petrified",
  "Poisoned", "Prone", "Restrained", "Stunned", "Unconscious",
];

const CONDITION_COLORS: Record<string, string> = {
  Blinded: "#888", Charmed: "#ff69b4", Deafened: "#888",
  Exhaustion: "#c0392b", Frightened: "#8e44ad", Grappled: "#d68910",
  Incapacitated: "#7f8c8d", Invisible: "#85c1e9", Paralyzed: "#c0392b",
  Petrified: "#95a5a6", Poisoned: "#27ae60", Prone: "#d35400",
  Restrained: "#d68910", Stunned: "#c0392b", Unconscious: "#7f8c8d",
};

// ── Sub-components ────────────────────────────────────────────────────────────

function DraggableBestiaryRow({ entry }: { entry: BestiaryEntry }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `bestiary-${entry.id}`,
    data: { entry },
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "6px 10px",
        borderRadius: 4,
        background: isDragging ? "var(--surface2)" : "transparent",
        cursor: "grab",
        opacity: isDragging ? 0.5 : 1,
        userSelect: "none",
      }}
    >
      <span style={{ fontSize: 10, color: "var(--text-muted)", opacity: 0.6 }}>⠿</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {entry.name}
        </div>
        <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
          CR {entry.cr} · AC {entry.ac} · HP {entry.maxHp}
        </div>
      </div>
    </div>
  );
}

function ConditionPill({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "1px 7px", borderRadius: 10, fontSize: 11,
      background: `${CONDITION_COLORS[label] ?? "#666"}22`,
      border: `1px solid ${CONDITION_COLORS[label] ?? "#666"}`,
      color: CONDITION_COLORS[label] ?? "#ccc",
    }}>
      {label}
      <button onClick={onRemove} style={{
        background: "none", padding: 0, color: "inherit",
        fontSize: 11, lineHeight: 1, width: 14, height: 14,
      }}>✕</button>
    </span>
  );
}

interface CombatantCardProps {
  c: Combatant;
  onUpdate: (id: string, patch: Partial<Combatant>) => void;
  onRemove: (id: string) => void;
  onRollInit: (c: Combatant) => void;
}

function CombatantCard({ c, onUpdate, onRemove, onRollInit }: CombatantCardProps) {
  const [showCondMenu, setShowCondMenu] = useState(false);
  const [deltaInput, setDeltaInput] = useState("");
  const [editInit, setEditInit] = useState(false);
  const [initVal, setInitVal] = useState(String(c.initiativeRoll));

  function applyDelta(heal: boolean) {
    const n = parseInt(deltaInput, 10);
    if (isNaN(n) || n <= 0) return;
    if (heal) onUpdate(c.id, { currentHp: Math.min(c.maxHp, c.currentHp + n) });
    else onUpdate(c.id, { currentHp: Math.max(0, c.currentHp - n) });
    setDeltaInput("");
  }

  function toggleCondition(cond: string) {
    const has = c.conditions.includes(cond);
    onUpdate(c.id, {
      conditions: has ? c.conditions.filter(x => x !== cond) : [...c.conditions, cond],
    });
  }

  const hpPct = c.maxHp > 0 ? Math.max(0, (c.currentHp / c.maxHp) * 100) : 100;
  const hpColor = hpPct > 50 ? "var(--success)" : hpPct > 25 ? "#e67e22" : "var(--danger)";
  const sourceColor = c.source === "player" ? "#5588cc" : c.source === "monster" ? "#c0392b" : "#888";

  return (
    <div style={{
      background: "var(--surface)",
      border: `1px solid ${c.isCurrentTurn ? "var(--accent)" : "var(--border)"}`,
      borderLeft: `4px solid ${c.isCurrentTurn ? "var(--accent)" : sourceColor}`,
      borderRadius: 6,
      padding: "10px 14px",
      boxShadow: c.isCurrentTurn ? "0 0 0 1px var(--accent)" : "none",
    }}>
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {/* Initiative — click to edit, 🎲 to roll */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 48 }}>
          {editInit ? (
            <input
              type="number"
              value={initVal}
              onChange={e => setInitVal(e.target.value)}
              onBlur={() => {
                const n = parseInt(initVal, 10);
                if (!isNaN(n)) onUpdate(c.id, { initiativeRoll: n });
                setEditInit(false);
              }}
              onKeyDown={e => {
                if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                if (e.key === "Escape") { setInitVal(String(c.initiativeRoll)); setEditInit(false); }
              }}
              autoFocus
              style={{ width: 48, textAlign: "center", padding: "2px 4px", fontSize: 18, fontWeight: 700 }}
            />
          ) : (
            <div
              onClick={() => { setEditInit(true); setInitVal(String(c.initiativeRoll)); }}
              title="Click to edit"
              style={{
                fontSize: 22, fontWeight: 800, lineHeight: 1,
                color: c.isCurrentTurn ? "var(--accent)" : "var(--text)",
                cursor: "pointer", textAlign: "center",
              }}
            >
              {c.initiativeRoll}
            </div>
          )}
          <button
            onClick={() => onRollInit(c)}
            title="Roll initiative"
            style={{ fontSize: 11, padding: "1px 4px", marginTop: 2, background: "var(--surface2)", color: "var(--text-muted)" }}
          >🎲</button>
        </div>

        {/* Name + AC */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 15, fontWeight: 700,
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>
            {c.isCurrentTurn && <span style={{ color: "var(--accent)", marginRight: 6 }}>▶</span>}
            {c.displayName}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
            AC {c.ac}
            <span style={{ marginLeft: 8, opacity: 0.6, textTransform: "uppercase", fontSize: 10 }}>
              {c.source}
            </span>
          </div>
        </div>

        {/* HP */}
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: hpColor }}>
            {c.currentHp}<span style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 400 }}>/{c.maxHp}</span>
          </div>
          <div style={{
            width: 72, height: 4, background: "var(--surface2)",
            borderRadius: 2, marginTop: 3, overflow: "hidden",
          }}>
            <div style={{ width: `${hpPct}%`, height: "100%", background: hpColor, transition: "width 0.2s" }} />
          </div>
        </div>

        <button onClick={() => onRemove(c.id)} className="ghost"
          style={{ padding: "2px 6px", fontSize: 13, color: "var(--danger)", borderColor: "var(--danger)" }}>
          ✕
        </button>
      </div>

      {/* HP controls */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8 }}>
        <input
          type="number"
          placeholder="amt"
          value={deltaInput}
          onChange={e => setDeltaInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") applyDelta(false); }}
          style={{ width: 60, padding: "3px 6px", fontSize: 12 }}
        />
        <button onClick={() => applyDelta(false)} className="danger" style={{ padding: "3px 10px", fontSize: 12 }}>
          − Dmg
        </button>
        <button onClick={() => applyDelta(true)} style={{ padding: "3px 10px", fontSize: 12, background: "var(--success)" }}>
          + Heal
        </button>

        <div style={{ marginLeft: "auto", position: "relative" }}>
          <button className="ghost" onClick={() => setShowCondMenu(v => !v)} style={{ fontSize: 12, padding: "3px 10px" }}>
            Conditions{c.conditions.length > 0 ? ` (${c.conditions.length})` : ""}
          </button>
          {showCondMenu && (
            <div style={{
              position: "absolute", right: 0, top: "100%", zIndex: 50, marginTop: 4,
              background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 6, padding: 10, width: 200,
              display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4,
            }}>
              {CONDITIONS.map(cond => (
                <label key={cond} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={c.conditions.includes(cond)}
                    onChange={() => toggleCondition(cond)}
                    style={{ width: "auto", accentColor: CONDITION_COLORS[cond] }}
                  />
                  {cond}
                </label>
              ))}
            </div>
          )}
        </div>
      </div>

      {c.conditions.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
          {c.conditions.map(cond => (
            <ConditionPill key={cond} label={cond} onRemove={() => toggleCondition(cond)} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Initiative() {
  const [combatants, setCombatants] = useState<Combatant[]>([]);
  const [round, setRound] = useState(1);

  const [bestiary, setBestiary] = useState<BestiaryEntry[]>([]);
  const [bestiarySearch, setBestiarySearch] = useState("");

  const [savedEncounters, setSavedEncounters] = useState<SavedEncounter[]>([]);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [showLoadDialog, setShowLoadDialog] = useState(false);
  const [saveName, setSaveName] = useState("");

  const [customName, setCustomName] = useState("");
  const [customAc, setCustomAc] = useState("10");
  const [customHp, setCustomHp] = useState("10");
  const [customInit, setCustomInit] = useState("0");

  const [toast, setToast] = useState<string | null>(null);

  const { setNodeRef: setDropRef, isOver } = useDroppable({ id: "initiative-zone" });

  const loadBestiary = useCallback(async () => {
    const res = await invoke<BestiaryEntry[]>("list_bestiary");
    setBestiary(res);
  }, []);

  const loadSaved = useCallback(async () => {
    const res = await invoke<SavedEncounter[]>("list_saved_encounters");
    setSavedEncounters(res);
  }, []);

  useEffect(() => {
    async function init() {
      const players = await invoke<Player[]>("list_players");
      setCombatants(players.map(p => ({
        id: `player-${p.id}`,
        source: "player",
        displayName: p.characterName,
        ac: p.ac,
        currentHp: p.maxHp,
        maxHp: p.maxHp,
        initiativeRoll: 0,
        initiativeMod: p.initiativeMod,
        conditions: [],
        isCurrentTurn: false,
      })));
      loadBestiary();
      loadSaved();
    }
    init();
  }, [loadBestiary, loadSaved]);

  const sorted = [...combatants].sort((a, b) => b.initiativeRoll - a.initiativeRoll);
  const filteredBestiary = bestiary.filter(e =>
    e.name.toLowerCase().includes(bestiarySearch.toLowerCase())
  );

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  // ── Mutations ─────────────────────────────────────────────────────────────
  function updateCombatant(id: string, patch: Partial<Combatant>) {
    setCombatants(prev => prev.map(c => c.id === id ? { ...c, ...patch } : c));
  }

  function removeCombatant(id: string) {
    setCombatants(prev => prev.filter(c => c.id !== id));
  }

  function addMonster(entry: BestiaryEntry) {
    const count = combatants.filter(c => c.displayName.startsWith(entry.name)).length;
    setCombatants(prev => [...prev, {
      id: `monster-${entry.id}-${Date.now()}`,
      source: "monster",
      displayName: count > 0 ? `${entry.name} ${count + 1}` : entry.name,
      ac: entry.ac,
      currentHp: entry.maxHp,
      maxHp: entry.maxHp,
      initiativeRoll: 0,
      initiativeMod: entry.initiativeMod,
      conditions: [],
      isCurrentTurn: false,
    }]);
  }

  function addCustom() {
    if (!customName.trim()) return;
    const hp = parseInt(customHp, 10) || 10;
    setCombatants(prev => [...prev, {
      id: `custom-${Date.now()}`,
      source: "custom",
      displayName: customName.trim(),
      ac: parseInt(customAc, 10) || 10,
      currentHp: hp,
      maxHp: hp,
      initiativeRoll: parseInt(customInit, 10) || 0,
      initiativeMod: 0,
      conditions: [],
      isCurrentTurn: false,
    }]);
    setCustomName(""); setCustomAc("10"); setCustomHp("10"); setCustomInit("0");
  }

  // ── Turn management ───────────────────────────────────────────────────────
  function startCombat() {
    if (sorted.length === 0) return;
    setCombatants(prev => prev.map(c => ({ ...c, isCurrentTurn: c.id === sorted[0].id })));
    setRound(1);
  }

  function nextTurn() {
    if (sorted.length === 0) return;
    const curIdx = sorted.findIndex(c => c.isCurrentTurn);
    const nextIdx = (curIdx + 1) % sorted.length;
    const wrapping = nextIdx === 0 && curIdx !== -1 && curIdx !== sorted.length - 1
      ? false
      : nextIdx === 0;
    setCombatants(prev => prev.map(c => ({ ...c, isCurrentTurn: c.id === sorted[nextIdx].id })));
    if (wrapping) setRound(r => r + 1);
  }

  function resetEncounter() {
    setCombatants(prev => prev.map(c => ({
      ...c,
      currentHp: c.maxHp,
      conditions: [],
      initiativeRoll: 0,
      isCurrentTurn: false,
    })));
    setRound(1);
  }

  // ── Dice ──────────────────────────────────────────────────────────────────
  async function rollInit(c: Combatant) {
    const mod = c.initiativeMod;
    const expr = `1d20${mod >= 0 ? "+" : ""}${mod}`;
    const res = await invoke<RollResult>("roll", { expr });
    updateCombatant(c.id, { initiativeRoll: res.total });
    showToast(`${c.displayName} rolled ${res.total} (${expr})`);
  }

  async function rollAllNpcInitiative() {
    const npcs = combatants.filter(c => c.source !== "player");
    if (npcs.length === 0) return;
    const results: { id: string; roll: number }[] = [];
    for (const c of npcs) {
      const mod = c.initiativeMod;
      const expr = `1d20${mod >= 0 ? "+" : ""}${mod}`;
      const res = await invoke<RollResult>("roll", { expr });
      results.push({ id: c.id, roll: res.total });
    }
    setCombatants(prev => prev.map(c => {
      const r = results.find(x => x.id === c.id);
      return r ? { ...c, initiativeRoll: r.roll } : c;
    }));
    showToast(`Rolled initiative for ${npcs.length} NPC${npcs.length !== 1 ? "s" : ""}`);
  }

  // ── Save / Load ───────────────────────────────────────────────────────────
  async function saveEncounter() {
    if (!saveName.trim()) return;
    await invoke("save_encounter", {
      encounter: {
        name: saveName.trim(),
        stateJson: JSON.stringify({ combatants, round }),
        updatedAt: null,
      },
    });
    await loadSaved();
    setShowSaveDialog(false);
    setSaveName("");
    showToast("Encounter saved.");
  }

  async function loadEncounter(enc: SavedEncounter) {
    try {
      const state = JSON.parse(enc.stateJson) as { combatants: Combatant[]; round: number };
      setCombatants(state.combatants);
      setRound(state.round);
      showToast(`Loaded "${enc.name}"`);
    } catch {
      alert("Failed to load: corrupted state.");
    }
    setShowLoadDialog(false);
  }

  async function deleteSaved(id: number) {
    if (!confirm("Delete this saved encounter?")) return;
    await invoke("delete_saved_encounter", { id });
    await loadSaved();
  }

  function handleDragEnd(event: DragEndEvent) {
    if (!event.over || event.over.id !== "initiative-zone") return;
    const entry = event.active.data.current?.entry as BestiaryEntry | undefined;
    if (entry) addMonster(entry);
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 0 }}>

        {/* Top bar */}
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          paddingBottom: 14, flexShrink: 0, flexWrap: "wrap",
        }}>
          <h1 style={{ fontSize: 20, fontWeight: 700 }}>Initiative Tracker</h1>

          <div style={{
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 6, padding: "4px 14px", fontSize: 15, fontWeight: 700,
          }}>
            Round {round}
          </div>

          <button onClick={startCombat} className="ghost" style={{ fontSize: 13 }}>⚔ Start</button>
          <button onClick={nextTurn} style={{ fontSize: 13 }}>▶ Next Turn</button>
          <button onClick={rollAllNpcInitiative} className="ghost" style={{ fontSize: 13 }}>🎲 Roll NPC Init</button>
          <button onClick={resetEncounter} className="ghost"
            style={{ fontSize: 13, color: "var(--danger)", borderColor: "var(--danger)" }}>
            ↺ Reset
          </button>

          <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
            <button className="ghost" style={{ fontSize: 13 }} onClick={() => { setShowLoadDialog(v => !v); setShowSaveDialog(false); }}>
              ↑ Load
            </button>
            <button className="ghost" style={{ fontSize: 13 }} onClick={() => { setShowSaveDialog(v => !v); setShowLoadDialog(false); }}>
              ↓ Save
            </button>
          </div>
        </div>

        {/* Toast */}
        {toast && (
          <div style={{
            background: "var(--surface2)", border: "1px solid var(--accent)",
            borderRadius: 4, padding: "5px 14px", marginBottom: 10,
            fontSize: 13, flexShrink: 0, color: "var(--text)",
          }}>
            🎲 {toast}
          </div>
        )}

        {/* Save dialog */}
        {showSaveDialog && (
          <div style={{
            background: "var(--surface)", border: "1px solid var(--accent)",
            borderRadius: 6, padding: 14, marginBottom: 12,
            display: "flex", gap: 8, alignItems: "center", flexShrink: 0,
          }}>
            <input
              value={saveName} onChange={e => setSaveName(e.target.value)}
              placeholder="Encounter name…" style={{ flex: 1 }} autoFocus
              onKeyDown={e => { if (e.key === "Enter") saveEncounter(); if (e.key === "Escape") setShowSaveDialog(false); }}
            />
            <button onClick={saveEncounter}>Save</button>
            <button className="ghost" onClick={() => setShowSaveDialog(false)}>Cancel</button>
          </div>
        )}

        {/* Load dialog */}
        {showLoadDialog && (
          <div style={{
            background: "var(--surface)", border: "1px solid var(--accent)",
            borderRadius: 6, padding: 14, marginBottom: 12, flexShrink: 0,
          }}>
            <div style={{ fontWeight: 600, marginBottom: 10 }}>Saved Encounters</div>
            {savedEncounters.length === 0 && (
              <div style={{ color: "var(--text-muted)", fontSize: 13 }}>No saved encounters yet.</div>
            )}
            {savedEncounters.map(enc => (
              <div key={enc.id} style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "7px 0", borderBottom: "1px solid var(--border)",
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{enc.name}</div>
                  {enc.updatedAt && <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{enc.updatedAt}</div>}
                </div>
                <button style={{ fontSize: 12, padding: "3px 10px" }} onClick={() => loadEncounter(enc)}>Load</button>
                <button className="danger" style={{ fontSize: 12, padding: "3px 10px" }} onClick={() => deleteSaved(enc.id!)}>✕</button>
              </div>
            ))}
            <button className="ghost" style={{ marginTop: 10, fontSize: 12 }} onClick={() => setShowLoadDialog(false)}>
              Close
            </button>
          </div>
        )}

        {/* Main 2-column area */}
        <div style={{ flex: 1, display: "flex", gap: 16, minHeight: 0 }}>

          {/* Left: combatant list (drop zone) */}
          <div
            ref={setDropRef}
            style={{
              flex: 1, overflowY: "auto",
              display: "flex", flexDirection: "column", gap: 8,
              border: `2px dashed ${isOver ? "var(--accent)" : "transparent"}`,
              borderRadius: 8, padding: isOver ? 8 : 0,
              transition: "border-color 0.15s",
            }}
          >
            {sorted.length === 0 && !isOver && (
              <div style={{
                margin: "auto", textAlign: "center",
                color: "var(--text-muted)", padding: 40,
              }}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>⚔</div>
                <div>Players from your Party Roster load automatically.</div>
                <div style={{ marginTop: 6, fontSize: 12 }}>
                  Drag monsters from the panel or click + to add them.
                </div>
              </div>
            )}
            {sorted.map(c => (
              <CombatantCard
                key={c.id}
                c={c}
                onUpdate={updateCombatant}
                onRemove={removeCombatant}
                onRollInit={rollInit}
              />
            ))}
            {isOver && (
              <div style={{
                border: "2px dashed var(--accent)", borderRadius: 6,
                padding: 20, textAlign: "center", color: "var(--accent)", fontSize: 13,
              }}>
                Drop to add to encounter
              </div>
            )}
          </div>

          {/* Right: bestiary + custom form */}
          <div style={{
            width: 264, flexShrink: 0,
            display: "flex", flexDirection: "column", gap: 12, overflowY: "auto",
          }}>

            {/* Stats chip */}
            <div style={{
              background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 6, padding: "8px 12px", fontSize: 12, color: "var(--text-muted)",
              display: "flex", justifyContent: "space-between",
            }}>
              <span>{combatants.length} combatant{combatants.length !== 1 ? "s" : ""}</span>
              <span>
                {combatants.filter(c => c.source === "player").length} players ·{" "}
                {combatants.filter(c => c.source !== "player").length} NPCs
              </span>
            </div>

            {/* Add custom */}
            <div style={{
              background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 6, padding: 12,
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--accent)", marginBottom: 8 }}>
                Add Custom
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <input value={customName} onChange={e => setCustomName(e.target.value)}
                  placeholder="Name *" style={{ fontSize: 12 }}
                  onKeyDown={e => { if (e.key === "Enter") addCustom(); }} />
                <div style={{ display: "flex", gap: 6 }}>
                  <label style={{ flex: 1, fontSize: 11, color: "var(--text-muted)" }}>
                    AC
                    <input value={customAc} onChange={e => setCustomAc(e.target.value)}
                      type="number" style={{ fontSize: 12, marginTop: 2 }} />
                  </label>
                  <label style={{ flex: 1, fontSize: 11, color: "var(--text-muted)" }}>
                    HP
                    <input value={customHp} onChange={e => setCustomHp(e.target.value)}
                      type="number" style={{ fontSize: 12, marginTop: 2 }} />
                  </label>
                  <label style={{ flex: 1, fontSize: 11, color: "var(--text-muted)" }}>
                    Init
                    <input value={customInit} onChange={e => setCustomInit(e.target.value)}
                      type="number" style={{ fontSize: 12, marginTop: 2 }} />
                  </label>
                </div>
                <button onClick={addCustom} style={{ fontSize: 12 }}>+ Add Combatant</button>
              </div>
            </div>

            {/* Bestiary panel */}
            <div style={{
              background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 6, padding: 12, flex: 1,
              display: "flex", flexDirection: "column", gap: 8, minHeight: 0,
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--accent)" }}>
                Bestiary{" "}
                <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(drag or +)</span>
              </div>
              <input
                value={bestiarySearch}
                onChange={e => setBestiarySearch(e.target.value)}
                placeholder="Search monsters…"
                style={{ fontSize: 12 }}
              />
              <div style={{ overflowY: "auto", flex: 1 }}>
                {filteredBestiary.length === 0 && (
                  <div style={{ color: "var(--text-muted)", fontSize: 12, padding: "8px 0" }}>
                    {bestiary.length === 0 ? "No bestiary entries. Import some!" : "No matches."}
                  </div>
                )}
                {filteredBestiary.map(entry => (
                  <div key={entry.id} style={{ display: "flex", alignItems: "center" }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <DraggableBestiaryRow entry={entry} />
                    </div>
                    <button
                      onClick={() => addMonster(entry)}
                      style={{ padding: "3px 9px", fontSize: 14, flexShrink: 0, marginRight: 6 }}
                      title={`Add ${entry.name}`}
                    >+</button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </DndContext>
  );
}
