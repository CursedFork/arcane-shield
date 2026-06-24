import { useEffect, useState, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import MarkdownView from "../components/MarkdownView";
import TagBadge from "../components/TagBadge";
import TagInput from "../components/TagInput";

interface Mechanic {
  id?: number;
  title: string;
  bodyMd: string;
  campaign: string | null;
  tags: string[];
}

const EMPTY: Mechanic = { title: "", bodyMd: "", campaign: null, tags: [] };

export default function Mechanics() {
  const [records, setRecords] = useState<Mechanic[]>([]);
  const [query, setQuery]     = useState("");
  const [selected, setSelected] = useState<Mechanic | null>(null);
  const [editing, setEditing]   = useState(false);
  const [form, setForm]         = useState<Mechanic>(EMPTY);
  const [error, setError]       = useState("");

  const load = useCallback(async () => {
    try {
      const res = await invoke<Mechanic[]>("search_mechanics", { query, campaign: null, tags: [] });
      setRecords(res);
    } catch (e) { console.error(e); }
  }, [query]);

  useEffect(() => { load(); }, [load]);

  function startCreate() { setForm(EMPTY); setSelected(null); setEditing(true); setError(""); }
  function startEdit(m: Mechanic) { setForm({ ...m }); setEditing(true); setError(""); }
  const f = (k: keyof Mechanic, v: unknown) => setForm((p) => ({ ...p, [k]: v }));

  async function save() {
    setError("");
    try {
      if (form.id) { await invoke("update_mechanic", { mechanic: form }); }
      else { await invoke("create_mechanic", { mechanic: form }); }
      setEditing(false); setSelected(null); await load();
    } catch (e) { setError(String(e)); }
  }

  async function del(id: number) {
    if (!confirm("Delete this mechanic?")) return;
    await invoke("delete_mechanic", { id });
    setSelected(null); setEditing(false); await load();
  }

  return (
    <div style={{ display: "flex", gap: 20, height: "100%" }}>
      {/* List */}
      <div style={{ width: 280, flexShrink: 0, display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700 }}>Mechanics</h1>
          <button onClick={startCreate} style={{ marginLeft: "auto", fontSize: 12, padding: "4px 10px" }}>+ New</button>
        </div>
        <input placeholder="Search…" value={query} onChange={(e) => setQuery(e.target.value)} />
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 2 }}>
          {records.length === 0 && <div style={{ color: "var(--text-muted)", fontSize: 13, padding: 8 }}>No mechanics found.</div>}
          {records.map((m) => (
            <button key={m.id} className="ghost"
              onClick={() => { setSelected(m); setEditing(false); }}
              style={{
                textAlign: "left", padding: "8px 12px", borderRadius: 4,
                background: selected?.id === m.id ? "var(--surface2)" : "transparent",
                borderColor: selected?.id === m.id ? "var(--accent)" : "transparent",
              }}>
              <div style={{ fontWeight: 500, fontSize: 13 }}>{m.title}</div>
              {m.campaign && <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{m.campaign}</div>}
            </button>
          ))}
        </div>
        <div style={{ color: "var(--text-muted)", fontSize: 12 }}>{records.length} mechanic{records.length !== 1 ? "s" : ""}</div>
      </div>

      {/* Detail / Edit */}
      <div style={{ flex: 1, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: 24, overflowY: "auto", display: "flex", flexDirection: "column", gap: 14 }}>
        {!selected && !editing && (
          <div style={{ color: "var(--text-muted)", margin: "auto" }}>Select a mechanic or create a new one.</div>
        )}

        {editing && (
          <>
            <h2 style={{ fontSize: 16 }}>{form.id ? "Edit Mechanic" : "New Mechanic"}</h2>
            {error && <div style={{ color: "var(--danger)", fontSize: 12 }}>{error}</div>}
            <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Title *
              <input value={form.title} onChange={(e) => f("title", e.target.value)} style={{ marginTop: 4 }} />
            </label>
            <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Campaign
              <input value={form.campaign ?? ""} onChange={(e) => f("campaign", e.target.value || null)} style={{ marginTop: 4 }} placeholder="optional" />
            </label>
            <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Body (Markdown)
              <textarea value={form.bodyMd} onChange={(e) => f("bodyMd", e.target.value)}
                rows={16} style={{ marginTop: 4, resize: "vertical", fontFamily: "monospace", fontSize: 12 }} />
            </label>
            <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Tags
              <div style={{ marginTop: 4 }}><TagInput value={form.tags} onChange={(tags) => f("tags", tags)} /></div>
            </label>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={save}>Save</button>
              <button className="ghost" onClick={() => setEditing(false)}>Cancel</button>
              {form.id && <button className="danger" style={{ marginLeft: "auto" }} onClick={() => del(form.id!)}>Delete</button>}
            </div>
          </>
        )}

        {!editing && selected && (
          <>
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 700 }}>{selected.title}</h2>
                {selected.campaign && <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>{selected.campaign}</div>}
              </div>
              <button className="ghost" onClick={() => startEdit(selected)}>Edit</button>
            </div>
            {selected.tags.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {selected.tags.map((t) => <TagBadge key={t} tag={t} />)}
              </div>
            )}
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14, flex: 1 }}>
              <MarkdownView content={selected.bodyMd} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
