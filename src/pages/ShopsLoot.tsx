import { useEffect, useState, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import CsvToolbar from "../components/CsvToolbar";

// ── Types ────────────────────────────────────────────────────────────────────

interface ShopItem  { id?: number; shopName: string; itemName: string; price: string; quantity: number; notes: string | null }
interface PartyItem { id?: number; itemName: string; owner: string; quantity: number; notes: string | null }
interface Player    { id?: number; playerName: string; characterName: string; ac: number; maxHp: number; initiativeMod: number; passivePerception: number; notes: string | null }

const EMPTY_SHOP:  ShopItem  = { shopName: "", itemName: "", price: "0 gp", quantity: 1, notes: null };
const EMPTY_PARTY: PartyItem = { itemName: "", owner: "party", quantity: 1, notes: null };
const EMPTY_PLAYER: Player   = { playerName: "", characterName: "", ac: 10, maxHp: 10, initiativeMod: 0, passivePerception: 10, notes: null };

type Tab = "shops" | "party" | "players";

// ── Helpers ──────────────────────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ fontSize: 12, color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: 4 }}>
      {label}{children}
    </label>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export default function ShopsLoot() {
  const [tab, setTab] = useState<Tab>("shops");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, height: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, marginRight: 20 }}>Shops & Loot</h1>
        {(["shops","party","players"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={tab === t ? "" : "ghost"}
            style={{ borderRadius: t === "shops" ? "4px 0 0 4px" : t === "players" ? "0 4px 4px 0" : "0", marginRight: -1, zIndex: tab === t ? 1 : 0 }}>
            {t === "shops" ? "Shops" : t === "party" ? "Party Loot" : "Party Roster"}
          </button>
        ))}
      </div>

      {tab === "shops"   && <ShopsTab />}
      {tab === "party"   && <PartyTab />}
      {tab === "players" && <PlayersTab />}
    </div>
  );
}

// ── Shops tab ────────────────────────────────────────────────────────────────

function ShopsTab() {
  const [items, setItems]       = useState<ShopItem[]>([]);
  const [filter, setFilter]     = useState("");
  const [shopFilter, setShop]   = useState("");
  const [editing, setEditing]   = useState(false);
  const [form, setForm]         = useState<ShopItem>(EMPTY_SHOP);
  const [error, setError]       = useState("");

  const load = useCallback(async () => {
    const res = await invoke<ShopItem[]>("list_shop_items");
    setItems(res);
  }, []);

  useEffect(() => { load(); }, [load]);

  const shops = [...new Set(items.map((i) => i.shopName))].sort();
  const visible = items.filter((i) =>
    (!filter    || i.itemName.toLowerCase().includes(filter.toLowerCase())) &&
    (!shopFilter || i.shopName === shopFilter)
  );

  const f = (k: keyof ShopItem, v: unknown) => setForm((p) => ({ ...p, [k]: v }));

  async function save() {
    setError("");
    try {
      if (form.id) await invoke("update_shop_item", { item: form });
      else         await invoke("create_shop_item", { item: form });
      setEditing(false); await load();
    } catch (e) { setError(String(e)); }
  }

  async function del(id: number) {
    if (!confirm("Delete?")) return;
    await invoke("delete_shop_item", { id }); await load();
  }

  return (
    <div style={{ display: "flex", gap: 20, flex: 1, minHeight: 0 }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10, minWidth: 0 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input placeholder="Search items…" value={filter} onChange={(e) => setFilter(e.target.value)} style={{ flex: 1, minWidth: 140 }} />
          <select value={shopFilter} onChange={(e) => setShop(e.target.value)} style={{ width: 160 }}>
            <option value="">All shops</option>
            {shops.map((s) => <option key={s}>{s}</option>)}
          </select>
          <button onClick={() => { setForm(EMPTY_SHOP); setEditing(true); setError(""); }}>+ Add Item</button>
        </div>
        <CsvToolbar table="shops" onImported={load} />
        <div style={{ flex: 1, overflowY: "auto", border: "1px solid var(--border)", borderRadius: 6 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--surface)", position: "sticky", top: 0 }}>
                {["Shop","Item","Price","Qty","Notes",""].map((h) => (
                  <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "var(--text-muted)", borderBottom: "1px solid var(--border)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.length === 0 && <tr><td colSpan={6} style={{ padding: 20, textAlign: "center", color: "var(--text-muted)" }}>No items.</td></tr>}
              {visible.map((i) => (
                <tr key={i.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "7px 12px" }}>{i.shopName}</td>
                  <td style={{ padding: "7px 12px", fontWeight: 500 }}>{i.itemName}</td>
                  <td style={{ padding: "7px 12px" }}>{i.price}</td>
                  <td style={{ padding: "7px 12px" }}>{i.quantity}</td>
                  <td style={{ padding: "7px 12px", color: "var(--text-muted)", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{i.notes ?? ""}</td>
                  <td style={{ padding: "7px 12px", whiteSpace: "nowrap" }}>
                    <button className="ghost" style={{ fontSize: 11, padding: "2px 8px", marginRight: 4 }} onClick={() => { setForm({ ...i }); setEditing(true); setError(""); }}>Edit</button>
                    <button className="ghost" style={{ fontSize: 11, padding: "2px 8px", color: "var(--danger)" }} onClick={() => del(i.id!)}>✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{visible.length} of {items.length} items</div>
      </div>

      {editing && (
        <div style={{ width: 300, flexShrink: 0, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: 20, display: "flex", flexDirection: "column", gap: 12, overflowY: "auto" }}>
          <h2 style={{ fontSize: 15 }}>{form.id ? "Edit" : "Add"} Shop Item</h2>
          {error && <div style={{ color: "var(--danger)", fontSize: 12 }}>{error}</div>}
          <Field label="Shop Name *"><input value={form.shopName} onChange={(e) => f("shopName", e.target.value)} /></Field>
          <Field label="Item Name *"><input value={form.itemName} onChange={(e) => f("itemName", e.target.value)} /></Field>
          <Field label="Price"><input value={form.price} onChange={(e) => f("price", e.target.value)} /></Field>
          <Field label="Quantity"><input type="number" min={0} value={form.quantity} onChange={(e) => f("quantity", Number(e.target.value))} /></Field>
          <Field label="Notes"><input value={form.notes ?? ""} onChange={(e) => f("notes", e.target.value || null)} /></Field>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={save}>Save</button>
            <button className="ghost" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Party loot tab ───────────────────────────────────────────────────────────

function PartyTab() {
  const [items, setItems]   = useState<PartyItem[]>([]);
  const [filter, setFilter] = useState("");
  const [editing, setEditing] = useState(false);
  const [form, setForm]     = useState<PartyItem>(EMPTY_PARTY);
  const [error, setError]   = useState("");

  const load = useCallback(async () => {
    setItems(await invoke<PartyItem[]>("list_party_items"));
  }, []);

  useEffect(() => { load(); }, [load]);

  const visible = items.filter((i) => !filter || i.itemName.toLowerCase().includes(filter.toLowerCase()));
  const f = (k: keyof PartyItem, v: unknown) => setForm((p) => ({ ...p, [k]: v }));

  async function save() {
    setError("");
    try {
      if (form.id) await invoke("update_party_item", { item: form });
      else         await invoke("create_party_item", { item: form });
      setEditing(false); await load();
    } catch (e) { setError(String(e)); }
  }

  async function del(id: number) {
    if (!confirm("Delete?")) return;
    await invoke("delete_party_item", { id }); await load();
  }

  return (
    <div style={{ display: "flex", gap: 20, flex: 1, minHeight: 0 }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10, minWidth: 0 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <input placeholder="Search loot…" value={filter} onChange={(e) => setFilter(e.target.value)} style={{ flex: 1 }} />
          <button onClick={() => { setForm(EMPTY_PARTY); setEditing(true); setError(""); }}>+ Add Item</button>
        </div>
        <CsvToolbar table="party_items" onImported={load} />
        <div style={{ flex: 1, overflowY: "auto", border: "1px solid var(--border)", borderRadius: 6 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--surface)", position: "sticky", top: 0 }}>
                {["Item","Owner","Qty","Notes",""].map((h) => (
                  <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "var(--text-muted)", borderBottom: "1px solid var(--border)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.length === 0 && <tr><td colSpan={5} style={{ padding: 20, textAlign: "center", color: "var(--text-muted)" }}>No loot.</td></tr>}
              {visible.map((i) => (
                <tr key={i.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "7px 12px", fontWeight: 500 }}>{i.itemName}</td>
                  <td style={{ padding: "7px 12px" }}>{i.owner}</td>
                  <td style={{ padding: "7px 12px" }}>{i.quantity}</td>
                  <td style={{ padding: "7px 12px", color: "var(--text-muted)" }}>{i.notes ?? ""}</td>
                  <td style={{ padding: "7px 12px", whiteSpace: "nowrap" }}>
                    <button className="ghost" style={{ fontSize: 11, padding: "2px 8px", marginRight: 4 }} onClick={() => { setForm({ ...i }); setEditing(true); setError(""); }}>Edit</button>
                    <button className="ghost" style={{ fontSize: 11, padding: "2px 8px", color: "var(--danger)" }} onClick={() => del(i.id!)}>✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{visible.length} items</div>
      </div>

      {editing && (
        <div style={{ width: 280, flexShrink: 0, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
          <h2 style={{ fontSize: 15 }}>{form.id ? "Edit" : "Add"} Item</h2>
          {error && <div style={{ color: "var(--danger)", fontSize: 12 }}>{error}</div>}
          <Field label="Item Name *"><input value={form.itemName} onChange={(e) => f("itemName", e.target.value)} /></Field>
          <Field label="Owner"><input value={form.owner} onChange={(e) => f("owner", e.target.value)} placeholder="party or player name" /></Field>
          <Field label="Quantity"><input type="number" min={0} value={form.quantity} onChange={(e) => f("quantity", Number(e.target.value))} /></Field>
          <Field label="Notes"><input value={form.notes ?? ""} onChange={(e) => f("notes", e.target.value || null)} /></Field>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={save}>Save</button>
            <button className="ghost" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Players / party roster tab ───────────────────────────────────────────────

function PlayersTab() {
  const [players, setPlayers]   = useState<Player[]>([]);
  const [editing, setEditing]   = useState(false);
  const [form, setForm]         = useState<Player>(EMPTY_PLAYER);
  const [error, setError]       = useState("");

  const load = useCallback(async () => {
    setPlayers(await invoke<Player[]>("list_players"));
  }, []);

  useEffect(() => { load(); }, [load]);

  const f = (k: keyof Player, v: unknown) => setForm((p) => ({ ...p, [k]: v }));

  async function save() {
    setError("");
    try {
      if (form.id) await invoke("update_player", { player: form });
      else         await invoke("create_player", { player: form });
      setEditing(false); await load();
    } catch (e) { setError(String(e)); }
  }

  async function del(id: number) {
    if (!confirm("Remove player?")) return;
    await invoke("delete_player", { id }); await load();
  }

  return (
    <div style={{ display: "flex", gap: 20, flex: 1, minHeight: 0 }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10, minWidth: 0 }}>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button onClick={() => { setForm(EMPTY_PLAYER); setEditing(true); setError(""); }}>+ Add Player</button>
        </div>
        <CsvToolbar table="players" onImported={load} />
        <div style={{ flex: 1, overflowY: "auto", border: "1px solid var(--border)", borderRadius: 6 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--surface)", position: "sticky", top: 0 }}>
                {["Character","Player","AC","Max HP","Init Mod","Pass Perc","Notes",""].map((h) => (
                  <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "var(--text-muted)", borderBottom: "1px solid var(--border)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {players.length === 0 && <tr><td colSpan={8} style={{ padding: 20, textAlign: "center", color: "var(--text-muted)" }}>No players yet. Add one or import a CSV.</td></tr>}
              {players.map((p) => (
                <tr key={p.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "7px 12px", fontWeight: 500 }}>{p.characterName}</td>
                  <td style={{ padding: "7px 12px", color: "var(--text-muted)" }}>{p.playerName}</td>
                  <td style={{ padding: "7px 12px" }}>{p.ac}</td>
                  <td style={{ padding: "7px 12px" }}>{p.maxHp}</td>
                  <td style={{ padding: "7px 12px" }}>{p.initiativeMod >= 0 ? `+${p.initiativeMod}` : p.initiativeMod}</td>
                  <td style={{ padding: "7px 12px" }}>{p.passivePerception}</td>
                  <td style={{ padding: "7px 12px", color: "var(--text-muted)", maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.notes ?? ""}</td>
                  <td style={{ padding: "7px 12px", whiteSpace: "nowrap" }}>
                    <button className="ghost" style={{ fontSize: 11, padding: "2px 8px", marginRight: 4 }} onClick={() => { setForm({ ...p }); setEditing(true); setError(""); }}>Edit</button>
                    <button className="ghost" style={{ fontSize: 11, padding: "2px 8px", color: "var(--danger)" }} onClick={() => del(p.id!)}>✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{players.length} player{players.length !== 1 ? "s" : ""}</div>
      </div>

      {editing && (
        <div style={{ width: 300, flexShrink: 0, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: 20, display: "flex", flexDirection: "column", gap: 12, overflowY: "auto" }}>
          <h2 style={{ fontSize: 15 }}>{form.id ? "Edit" : "Add"} Player</h2>
          {error && <div style={{ color: "var(--danger)", fontSize: 12 }}>{error}</div>}
          <Field label="Character Name *"><input value={form.characterName} onChange={(e) => f("characterName", e.target.value)} /></Field>
          <Field label="Player Name *"><input value={form.playerName} onChange={(e) => f("playerName", e.target.value)} /></Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <Field label="AC"><input type="number" value={form.ac} onChange={(e) => f("ac", Number(e.target.value))} /></Field>
            <Field label="Max HP"><input type="number" value={form.maxHp} onChange={(e) => f("maxHp", Number(e.target.value))} /></Field>
            <Field label="Init Mod"><input type="number" value={form.initiativeMod} onChange={(e) => f("initiativeMod", Number(e.target.value))} /></Field>
            <Field label="Pass Perc"><input type="number" value={form.passivePerception} onChange={(e) => f("passivePerception", Number(e.target.value))} /></Field>
          </div>
          <Field label="Notes"><textarea value={form.notes ?? ""} onChange={(e) => f("notes", e.target.value || null)} rows={2} style={{ resize: "vertical" }} /></Field>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={save}>Save</button>
            <button className="ghost" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
