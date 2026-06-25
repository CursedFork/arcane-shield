import { useEffect, useState, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { open } from "@tauri-apps/plugin-dialog";

interface FileImportResult {
  path: string;
  filename: string;
  table: string;
  status: "ok" | "unknown" | "error";
  inserted: number;
  skippedRows: number;
  errors: string[];
}

const TABLE_LABELS: Record<string, string> = {
  players:     "Players / Roster",
  magic_items: "Magic Items",
  bestiary:    "Bestiary",
  mechanics:   "Mechanics",
  campaigns:   "Campaigns",
  notes:       "Session Notes",
  shops:       "Shops",
  party_items: "Party Loot",
};

const TABLE_COLUMNS: Record<string, string> = {
  players:     "player_name, character_name, ac, max_hp, initiative_mod, passive_perception, notes",
  magic_items: "name, item_type, rarity, requires_attunement, attunement_requirement, description, mechanical_effect, charges, source_campaign, tags",
  bestiary:    "name, ac, max_hp, initiative_mod, cr, statblock_md, tags",
  mechanics:   "title, body_md, campaign, tags",
  campaigns:   "title, body_md, tags",
  notes:       "session_label, note_date, body",
  shops:       "shop_name, item_name, price, quantity, notes",
  party_items: "item_name, owner, quantity, notes",
};

export default function BulkImport() {
  const [results, setResults]   = useState<FileImportResult[]>([]);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy]         = useState(false);

  const runImport = useCallback(async (paths: string[]) => {
    if (paths.length === 0) return;
    setBusy(true);
    setResults([]);
    try {
      const res = await invoke<FileImportResult[]>("import_paths", { paths });
      setResults(res);
    } catch (e) {
      setResults([{ path: "", filename: "error", table: "unknown", status: "error", inserted: 0, skippedRows: 0, errors: [String(e)] }]);
    } finally {
      setBusy(false);
    }
  }, []);

  // Tauri webview-level drag-drop events
  useEffect(() => {
    let unlisten: (() => void) | undefined;

    getCurrentWebview().onDragDropEvent((e) => {
      const { type } = e.payload;
      if (type === "enter" || type === "over") setDragging(true);
      if (type === "leave") setDragging(false);
      if (type === "drop") {
        setDragging(false);
        runImport(e.payload.paths);
      }
    }).then(fn => { unlisten = fn; });

    return () => { unlisten?.(); };
  }, [runImport]);

  async function pickFolder() {
    const selected = await open({ directory: true, multiple: true, title: "Select folder(s) with CSV files" });
    if (!selected) return;
    const paths = Array.isArray(selected) ? selected : [selected];
    runImport(paths);
  }

  async function pickFiles() {
    const selected = await open({ multiple: true, filters: [{ name: "CSV", extensions: ["csv"] }], title: "Select CSV files" });
    if (!selected) return;
    const paths = Array.isArray(selected) ? selected : [selected];
    runImport(paths);
  }

  async function downloadTemplate(table: string) {
    const csv = await invoke<string>("csv_template", { table });
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = `${table}_template.csv`; a.click();
    URL.revokeObjectURL(url);
  }

  const totalInserted = results.reduce((s, r) => s + r.inserted, 0);
  const okCount       = results.filter(r => r.status === "ok").length;
  const errCount      = results.filter(r => r.status === "error" || r.status === "unknown").length;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 20 }}>
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Bulk CSV Import</h1>
        <p style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 4 }}>
          Drop a folder (or individual CSV files) anywhere on this page. Tables are detected automatically from column headers or filename.
        </p>
      </div>

      {/* Drop zone */}
      <div style={{
        border: `2px dashed ${dragging ? "var(--accent)" : "var(--border)"}`,
        borderRadius: 12,
        padding: "48px 24px",
        textAlign: "center",
        background: dragging ? "rgba(124,92,191,0.08)" : "var(--surface)",
        transition: "border-color 0.15s, background 0.15s",
        flexShrink: 0,
      }}>
        {busy ? (
          <div style={{ color: "var(--text-muted)", fontSize: 15 }}>Importing…</div>
        ) : dragging ? (
          <div style={{ color: "var(--accent)", fontSize: 18, fontWeight: 700 }}>Drop to import</div>
        ) : (
          <>
            <div style={{ fontSize: 40, marginBottom: 12 }}>📂</div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>
              Drag a folder or CSV files here
            </div>
            <div style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 20 }}>
              or use the buttons below
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
              <button onClick={pickFolder} style={{ fontSize: 13 }}>📁 Choose Folder</button>
              <button onClick={pickFiles} className="ghost" style={{ fontSize: 13 }}>📄 Choose CSV Files</button>
            </div>
          </>
        )}
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Summary */}
          <div style={{
            display: "flex", gap: 16, padding: "10px 16px",
            background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8,
            fontSize: 13, flexWrap: "wrap",
          }}>
            <span><strong style={{ color: "var(--accent)" }}>{results.length}</strong> file{results.length !== 1 ? "s" : ""} processed</span>
            <span><strong style={{ color: "var(--success)" }}>{totalInserted}</strong> rows inserted</span>
            {okCount > 0 && <span style={{ color: "var(--success)" }}>✓ {okCount} imported</span>}
            {errCount > 0 && <span style={{ color: "var(--danger)" }}>✕ {errCount} failed/unknown</span>}
          </div>

          {/* Per-file cards */}
          {results.map((res, i) => (
            <div key={i} style={{
              background: "var(--surface)",
              border: `1px solid ${res.status === "ok" ? "var(--success)" : res.status === "unknown" ? "var(--border)" : "var(--danger)"}`,
              borderLeft: `4px solid ${res.status === "ok" ? "var(--success)" : res.status === "unknown" ? "var(--text-muted)" : "var(--danger)"}`,
              borderRadius: 6, padding: "12px 16px",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: res.errors.length > 0 ? 8 : 0 }}>
                <span style={{ fontSize: 16 }}>
                  {res.status === "ok" ? "✓" : res.status === "unknown" ? "?" : "✕"}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{res.filename}</div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                    {res.status === "unknown"
                      ? "Could not detect table — rename file or check headers"
                      : `→ ${TABLE_LABELS[res.table] ?? res.table} · ${res.inserted} inserted${res.skippedRows > 0 ? ` · ${res.skippedRows} skipped` : ""}`}
                  </div>
                </div>
                {res.status === "ok" && (
                  <span style={{
                    background: "rgba(39,174,96,0.15)", color: "var(--success)",
                    border: "1px solid var(--success)", borderRadius: 4,
                    padding: "1px 8px", fontSize: 11, fontWeight: 600,
                  }}>
                    {TABLE_LABELS[res.table] ?? res.table}
                  </span>
                )}
              </div>
              {res.errors.length > 0 && (
                <div style={{
                  background: "rgba(192,57,43,0.08)", borderRadius: 4,
                  padding: "6px 10px", fontSize: 12,
                }}>
                  {res.errors.slice(0, 5).map((e, j) => (
                    <div key={j} style={{ color: "var(--danger)" }}>{e}</div>
                  ))}
                  {res.errors.length > 5 && (
                    <div style={{ color: "var(--text-muted)" }}>…and {res.errors.length - 5} more</div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Template reference */}
      {results.length === 0 && !busy && (
        <div style={{
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 8, padding: 16,
        }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--accent)", marginBottom: 12 }}>
            CSV Column Reference
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {Object.entries(TABLE_LABELS).map(([table, label]) => (
              <div key={table} style={{ display: "flex", alignItems: "baseline", gap: 10, fontSize: 12 }}>
                <button
                  onClick={() => downloadTemplate(table)}
                  className="ghost"
                  style={{ fontSize: 11, padding: "1px 8px", flexShrink: 0 }}
                >
                  ↓ {label}
                </button>
                <span style={{ color: "var(--text-muted)", fontFamily: "monospace" }}>
                  {TABLE_COLUMNS[table]}
                </span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 12, fontSize: 11, color: "var(--text-muted)" }}>
            Tags columns: semicolon-separated values, e.g. <code style={{ background: "var(--surface2)", padding: "1px 5px", borderRadius: 3 }}>Combat;Fire;Legendary</code>
          </div>
        </div>
      )}
    </div>
  );
}
