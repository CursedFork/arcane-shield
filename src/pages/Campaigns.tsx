import { useEffect, useState, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import MarkdownView from "../components/MarkdownView";
import TagBadge from "../components/TagBadge";
import TagInput from "../components/TagInput";

interface Campaign {
  id?: number;
  title: string;
  bodyMd: string;
  tags: string[];
}

const EMPTY: Campaign = { title: "", bodyMd: "", tags: [] };

export default function Campaigns() {
  const [records, setRecords]   = useState<Campaign[]>([]);
  const [query, setQuery]       = useState("");
  const [selected, setSelected] = useState<Campaign | null>(null);
  const [editing, setEditing]   = useState(false);
  const [form, setForm]         = useState<Campaign>(EMPTY);
  const [error, setError]       = useState("");

  const load = useCallback(async () => {
    try {
      const res = await invoke<Campaign[]>("search_campaigns", { query, tags: [] });
      setRecords(res);
    } catch (e) { console.error(e); }
  }, [query]);

  useEffect(() => { load(); }, [load]);

  function startCreate() { setForm(EMPTY); setSelected(null); setEditing(true); setError(""); }
  function startEdit(c: Campaign) { setForm({ ...c }); setEditing(true); setError(""); }
  const f = (k: keyof Campaign, v: unknown) => setForm((p) => ({ ...p, [k]: v }));

  async function save() {
    setError("");
    try {
      if (form.id) { await invoke("update_campaign", { campaign: form }); }
      else { await invoke("create_campaign", { campaign: form }); }
      setEditing(false); setSelected(null); await load();
    } catch (e) { setError(String(e)); }
  }

  async function del(id: number) {
    if (!confirm("Delete this campaign entry?")) return;
    await invoke("delete_campaign", { id });
    setSelected(null); setEditing(false); await load();
  }

  return (
    <div style={{ display: "flex", gap: 20, height: "100%" }}>
      {/* List */}
      <div style={{ width: 280, flexShrink: 0, display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700 }}>Campaigns</h1>
          <button onClick={startCreate} style={{ marginLeft: "auto", fontSize: 12, padding: "4px 10px" }}>+ New</button>
        </div>
        <input placeholder="Search…" value={query} onChange={(e) => setQuery(e.target.value)} />
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 2 }}>
          {records.length === 0 && <div style={{ color: "var(--text-muted)", fontSize: 13, padding: 8 }}>No campaign entries found.</div>}
          {records.map((c) => (
            <button key={c.id} className="ghost"
              onClick={() => { setSelected(c); setEditing(false); }}
              style={{
                textAlign: "left", padding: "8px 12px", borderRadius: 4,
                background: selected?.id === c.id ? "var(--surface2)" : "transparent",
                borderColor: selected?.id === c.id ? "var(--accent)" : "transparent",
              }}>
              <div style={{ fontWeight: 500, fontSize: 13 }}>{c.title}</div>
              {c.tags.length > 0 && (
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{c.tags.slice(0, 3).join(", ")}</div>
              )}
            </button>
          ))}
        </div>
        <div style={{ color: "var(--text-muted)", fontSize: 12 }}>{records.length} entr{records.length !== 1 ? "ies" : "y"}</div>
      </div>

      {/* Detail / Edit */}
      <div style={{ flex: 1, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: 24, overflowY: "auto", display: "flex", flexDirection: "column", gap: 14 }}>
        {!selected && !editing && (
          <div style={{ color: "var(--text-muted)", margin: "auto" }}>Select an entry or create a new one.</div>
        )}

        {editing && (
          <>
            <h2 style={{ fontSize: 16 }}>{form.id ? "Edit Campaign Entry" : "New Campaign Entry"}</h2>
            {error && <div style={{ color: "var(--danger)", fontSize: 12 }}>{error}</div>}
            <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Title *
              <input value={form.title} onChange={(e) => f("title", e.target.value)} style={{ marginTop: 4 }} />
            </label>
            <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Body (Markdown)
              <textarea value={form.bodyMd} onChange={(e) => f("bodyMd", e.target.value)}
                rows={18} style={{ marginTop: 4, resize: "vertical", fontFamily: "monospace", fontSize: 12 }} />
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
              <h2 style={{ fontSize: 18, fontWeight: 700 }}>{selected.title}</h2>
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
