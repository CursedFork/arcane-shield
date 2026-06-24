import { useEffect, useState, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import TagBadge from "../components/TagBadge";
import TagInput from "../components/TagInput";

interface MagicItem {
  id?: number;
  name: string;
  itemType: string;
  rarity: string;
  requiresAttunement: boolean;
  attunementRequirement: string | null;
  description: string;
  mechanicalEffect: string;
  charges: number | null;
  sourceCampaign: string | null;
  tags: string[];
}

const EMPTY: MagicItem = {
  name: "", itemType: "Wondrous", rarity: "Common",
  requiresAttunement: false, attunementRequirement: null,
  description: "", mechanicalEffect: "",
  charges: null, sourceCampaign: null, tags: [],
};

const ITEM_TYPES = ["Wondrous","Weapon","Armor","Potion","Ring","Wand","Staff","Rod","Scroll","Other"];
const RARITIES   = ["Common","Uncommon","Rare","Very Rare","Legendary","Artifact"];

const RARITY_COLOR: Record<string, string> = {
  Common: "#aaa", Uncommon: "#1eff00", Rare: "#0070dd",
  "Very Rare": "#a335ee", Legendary: "#ff8000", Artifact: "#e6cc80",
};

export default function Items() {
  const [items, setItems]       = useState<MagicItem[]>([]);
  const [query, setQuery]       = useState("");
  const [typeFilter, setType]   = useState("");
  const [rarityFilter, setRarity] = useState("");
  const [sortBy, setSort]       = useState("name");
  const [selected, setSelected] = useState<MagicItem | null>(null);
  const [editing, setEditing]   = useState(false);
  const [form, setForm]         = useState<MagicItem>(EMPTY);
  const [error, setError]       = useState("");

  const load = useCallback(async () => {
    try {
      const result = await invoke<MagicItem[]>("search_items", {
        query, itemType: typeFilter || null, rarity: rarityFilter || null,
        tags: [], sortBy,
      });
      setItems(result);
    } catch (e) { console.error(e); }
  }, [query, typeFilter, rarityFilter, sortBy]);

  useEffect(() => { load(); }, [load]);

  function startCreate() {
    setForm(EMPTY);
    setSelected(null);
    setEditing(true);
    setError("");
  }

  function startEdit(item: MagicItem) {
    setForm({ ...item });
    setEditing(true);
    setError("");
  }

  async function save() {
    setError("");
    try {
      if (form.id) {
        await invoke("update_item", { item: form });
      } else {
        await invoke("create_item", { item: form });
      }
      setEditing(false);
      setSelected(null);
      await load();
    } catch (e) { setError(String(e)); }
  }

  async function del(id: number) {
    if (!confirm("Delete this item?")) return;
    await invoke("delete_item", { id });
    setSelected(null);
    setEditing(false);
    await load();
  }

  const f = (k: keyof MagicItem, v: unknown) => setForm((p) => ({ ...p, [k]: v }));

  return (
    <div style={{ display: "flex", gap: 20, height: "100%" }}>
      {/* Left: list */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12, minWidth: 0 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, flexShrink: 0 }}>Magic Items</h1>
          <button onClick={startCreate} style={{ marginLeft: "auto", flexShrink: 0 }}>+ New Item</button>
        </div>

        {/* Filters */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input placeholder="Search by name…" value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ flex: 1, minWidth: 160 }} />
          <select value={typeFilter} onChange={(e) => setType(e.target.value)} style={{ width: 130 }}>
            <option value="">All types</option>
            {ITEM_TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>
          <select value={rarityFilter} onChange={(e) => setRarity(e.target.value)} style={{ width: 130 }}>
            <option value="">All rarities</option>
            {RARITIES.map((r) => <option key={r}>{r}</option>)}
          </select>
          <select value={sortBy} onChange={(e) => setSort(e.target.value)} style={{ width: 110 }}>
            <option value="name">Sort: Name</option>
            <option value="rarity">Sort: Rarity</option>
            <option value="item_type">Sort: Type</option>
          </select>
        </div>

        {/* Table */}
        <div style={{ flex: 1, overflowY: "auto", borderRadius: 6, border: "1px solid var(--border)" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--surface)", position: "sticky", top: 0 }}>
                {["Name","Type","Rarity","Attune","Charges"].map((h) => (
                  <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "var(--text-muted)", fontWeight: 600, borderBottom: "1px solid var(--border)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr><td colSpan={5} style={{ padding: 24, textAlign: "center", color: "var(--text-muted)" }}>No items found.</td></tr>
              )}
              {items.map((item) => (
                <tr key={item.id}
                  onClick={() => { setSelected(item); setEditing(false); }}
                  style={{
                    cursor: "pointer",
                    background: selected?.id === item.id ? "var(--surface2)" : "transparent",
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  <td style={{ padding: "8px 12px", fontWeight: 500 }}>{item.name}</td>
                  <td style={{ padding: "8px 12px", color: "var(--text-muted)" }}>{item.itemType}</td>
                  <td style={{ padding: "8px 12px", color: RARITY_COLOR[item.rarity] ?? "var(--text)" }}>{item.rarity}</td>
                  <td style={{ padding: "8px 12px" }}>{item.requiresAttunement ? "✓" : "—"}</td>
                  <td style={{ padding: "8px 12px", color: "var(--text-muted)" }}>{item.charges ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ color: "var(--text-muted)", fontSize: 12 }}>{items.length} item{items.length !== 1 ? "s" : ""}</div>
      </div>

      {/* Right: detail / edit panel */}
      {(selected || editing) && (
        <div style={{
          width: 380, flexShrink: 0, background: "var(--surface)",
          border: "1px solid var(--border)", borderRadius: 8,
          padding: 20, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12,
        }}>
          {editing ? (
            <>
              <h2 style={{ fontSize: 16 }}>{form.id ? "Edit Item" : "New Item"}</h2>
              {error && <div style={{ color: "var(--danger)", fontSize: 12 }}>{error}</div>}

              <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Name *
                <input value={form.name} onChange={(e) => f("name", e.target.value)} style={{ marginTop: 4 }} />
              </label>

              <div style={{ display: "flex", gap: 8 }}>
                <label style={{ flex: 1, fontSize: 12, color: "var(--text-muted)" }}>Type *
                  <select value={form.itemType} onChange={(e) => f("itemType", e.target.value)} style={{ marginTop: 4 }}>
                    {ITEM_TYPES.map((t) => <option key={t}>{t}</option>)}
                  </select>
                </label>
                <label style={{ flex: 1, fontSize: 12, color: "var(--text-muted)" }}>Rarity *
                  <select value={form.rarity} onChange={(e) => f("rarity", e.target.value)} style={{ marginTop: 4 }}>
                    {RARITIES.map((r) => <option key={r}>{r}</option>)}
                  </select>
                </label>
              </div>

              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                <input type="checkbox" checked={form.requiresAttunement}
                  onChange={(e) => f("requiresAttunement", e.target.checked)}
                  style={{ width: "auto" }} />
                Requires Attunement
              </label>

              {form.requiresAttunement && (
                <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Attunement Requirement
                  <input value={form.attunementRequirement ?? ""}
                    onChange={(e) => f("attunementRequirement", e.target.value || null)}
                    placeholder="e.g. by a spellcaster"
                    style={{ marginTop: 4 }} />
                </label>
              )}

              <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Description *
                <textarea value={form.description} onChange={(e) => f("description", e.target.value)}
                  rows={3} style={{ marginTop: 4, resize: "vertical" }} />
              </label>

              <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Mechanical Effect *
                <textarea value={form.mechanicalEffect} onChange={(e) => f("mechanicalEffect", e.target.value)}
                  rows={3} style={{ marginTop: 4, resize: "vertical" }} />
              </label>

              <div style={{ display: "flex", gap: 8 }}>
                <label style={{ flex: 1, fontSize: 12, color: "var(--text-muted)" }}>Charges
                  <input type="number" min={0} value={form.charges ?? ""}
                    onChange={(e) => f("charges", e.target.value === "" ? null : Number(e.target.value))}
                    style={{ marginTop: 4 }} />
                </label>
                <label style={{ flex: 1, fontSize: 12, color: "var(--text-muted)" }}>Source Campaign
                  <input value={form.sourceCampaign ?? ""}
                    onChange={(e) => f("sourceCampaign", e.target.value || null)}
                    style={{ marginTop: 4 }} />
                </label>
              </div>

              <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Tags
                <div style={{ marginTop: 4 }}>
                  <TagInput value={form.tags} onChange={(tags) => f("tags", tags)} />
                </div>
              </label>

              <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                <button onClick={save}>Save</button>
                <button className="ghost" onClick={() => { setEditing(false); }}>Cancel</button>
                {form.id && <button className="danger" style={{ marginLeft: "auto" }} onClick={() => del(form.id!)}>Delete</button>}
              </div>
            </>
          ) : selected ? (
            <>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
                <div>
                  <h2 style={{ fontSize: 17, fontWeight: 700 }}>{selected.name}</h2>
                  <div style={{ color: RARITY_COLOR[selected.rarity] ?? "var(--text)", fontSize: 13, marginTop: 2 }}>
                    {selected.rarity} {selected.itemType}
                    {selected.requiresAttunement && <span style={{ color: "var(--text-muted)" }}> · requires attunement{selected.attunementRequirement ? ` ${selected.attunementRequirement}` : ""}</span>}
                  </div>
                </div>
                <button className="ghost" onClick={() => startEdit(selected)}>Edit</button>
              </div>

              {selected.charges != null && (
                <div style={{ fontSize: 13 }}><span style={{ color: "var(--text-muted)" }}>Charges: </span>{selected.charges}</div>
              )}
              {selected.sourceCampaign && (
                <div style={{ fontSize: 13 }}><span style={{ color: "var(--text-muted)" }}>Campaign: </span>{selected.sourceCampaign}</div>
              )}

              <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <div style={{ color: "var(--text-muted)", fontSize: 11, marginBottom: 6 }}>DESCRIPTION</div>
                <p style={{ fontSize: 13, lineHeight: 1.6 }}>{selected.description}</p>
              </div>

              <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <div style={{ color: "var(--text-muted)", fontSize: 11, marginBottom: 6 }}>MECHANICAL EFFECT</div>
                <p style={{ fontSize: 13, lineHeight: 1.6 }}>{selected.mechanicalEffect}</p>
              </div>

              {selected.tags.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {selected.tags.map((t) => <TagBadge key={t} tag={t} />)}
                </div>
              )}

              <button className="danger ghost" style={{ marginTop: 4, border: "1px solid var(--danger)", color: "var(--danger)", background: "transparent" }}
                onClick={() => del(selected.id!)}>Delete Item</button>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}
