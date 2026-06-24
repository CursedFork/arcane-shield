import { useEffect, useState, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import CsvToolbar from "../components/CsvToolbar";

interface Note {
  id?: number;
  sessionLabel: string;
  noteDate: string;
  body: string;
  createdAt?: string;
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

type SessionGroup = { label: string; notes: Note[] };

function groupBySession(notes: Note[]): SessionGroup[] {
  const map = new Map<string, Note[]>();
  for (const n of notes) {
    if (!map.has(n.sessionLabel)) map.set(n.sessionLabel, []);
    map.get(n.sessionLabel)!.push(n);
  }
  return Array.from(map.entries()).map(([label, notes]) => ({ label, notes }));
}

export default function Notes() {
  const [notes, setNotes]       = useState<Note[]>([]);
  const [editId, setEditId]     = useState<number | null>(null);
  const [editBody, setEditBody] = useState("");

  // Quick-add form state
  const [qSession, setQSession] = useState("");
  const [qDate, setQDate]       = useState(today());
  const [qBody, setQBody]       = useState("");
  const [qError, setQError]     = useState("");

  const load = useCallback(async () => {
    const res = await invoke<Note[]>("list_notes");
    setNotes(res);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function addNote() {
    setQError("");
    if (!qBody.trim()) { setQError("Body is required."); return; }
    if (!qSession.trim()) { setQError("Session label is required."); return; }
    try {
      await invoke("create_note", { note: { sessionLabel: qSession, noteDate: qDate, body: qBody } });
      setQBody("");
      await load();
    } catch (e) { setQError(String(e)); }
  }

  async function saveEdit(note: Note) {
    await invoke("update_note", { note: { ...note, body: editBody } });
    setEditId(null);
    await load();
  }

  async function del(id: number) {
    if (!confirm("Delete this note?")) return;
    await invoke("delete_note", { id });
    await load();
  }

  const groups = groupBySession(notes);

  return (
    <div style={{ display: "flex", gap: 20, height: "100%", minHeight: 0 }}>
      {/* Left: quick-add + CSV */}
      <div style={{ width: 300, flexShrink: 0, display: "flex", flexDirection: "column", gap: 14 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Session Notes</h1>

        {/* Quick-add */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--accent)" }}>Quick Add</div>
          {qError && <div style={{ fontSize: 12, color: "var(--danger)" }}>{qError}</div>}
          <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Session *
            <input value={qSession} onChange={(e) => setQSession(e.target.value)}
              placeholder="Session 12" style={{ marginTop: 4 }} />
          </label>
          <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Date *
            <input type="date" value={qDate} onChange={(e) => setQDate(e.target.value)} style={{ marginTop: 4 }} />
          </label>
          <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Note *
            <textarea value={qBody} onChange={(e) => setQBody(e.target.value)}
              placeholder="What happened…" rows={5}
              style={{ marginTop: 4, resize: "vertical" }}
              onKeyDown={(e) => { if (e.key === "Enter" && e.ctrlKey) addNote(); }} />
          </label>
          <button onClick={addNote}>Add Note <span style={{ opacity: 0.6, fontSize: 11 }}>Ctrl+Enter</span></button>
        </div>

        {/* CSV */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)" }}>CSV IMPORT / EXPORT</div>
          <CsvToolbar table="notes" onImported={load} />
        </div>

        <div style={{ color: "var(--text-muted)", fontSize: 12 }}>{notes.length} note{notes.length !== 1 ? "s" : ""}</div>
      </div>

      {/* Right: grouped notes list */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 24 }}>
        {groups.length === 0 && (
          <div style={{ color: "var(--text-muted)", margin: "auto" }}>No notes yet. Add one on the left.</div>
        )}
        {groups.map((g) => (
          <div key={g.label}>
            <div style={{ fontSize: 13, fontWeight: 700, color: "var(--accent)", marginBottom: 8, letterSpacing: 0.5 }}>
              {g.label}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {g.notes.map((n) => (
                <div key={n.id} style={{
                  background: "var(--surface)", border: "1px solid var(--border)",
                  borderRadius: 6, padding: "12px 16px",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{n.noteDate}</span>
                    <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                      {editId === n.id ? (
                        <>
                          <button style={{ fontSize: 12, padding: "2px 10px" }} onClick={() => saveEdit(n)}>Save</button>
                          <button className="ghost" style={{ fontSize: 12, padding: "2px 10px" }} onClick={() => setEditId(null)}>Cancel</button>
                        </>
                      ) : (
                        <>
                          <button className="ghost" style={{ fontSize: 12, padding: "2px 10px" }}
                            onClick={() => { setEditId(n.id!); setEditBody(n.body); }}>Edit</button>
                          <button className="ghost" style={{ fontSize: 12, padding: "2px 10px", color: "var(--danger)", borderColor: "var(--danger)" }}
                            onClick={() => del(n.id!)}>✕</button>
                        </>
                      )}
                    </div>
                  </div>

                  {editId === n.id ? (
                    <textarea value={editBody} onChange={(e) => setEditBody(e.target.value)}
                      rows={4} style={{ resize: "vertical", width: "100%" }} autoFocus />
                  ) : (
                    <p style={{ fontSize: 13, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{n.body}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
