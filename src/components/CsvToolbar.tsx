import { useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

interface Report { inserted: number; skipped: number; errors: string[] }

interface Props {
  table: string;
  onImported: () => void;
}

function downloadText(text: string, filename: string) {
  const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

export default function CsvToolbar({ table, onImported }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [busy, setBusy]     = useState(false);

  async function getTemplate() {
    const csv = await invoke<string>("csv_template", { table });
    downloadText(csv, `${table}_template.csv`);
  }

  async function doExport() {
    const csv = await invoke<string>("export_csv", { table });
    downloadText(csv, `${table}_export.csv`);
  }

  async function doImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setReport(null);
    try {
      const text = await file.text();
      const rep  = await invoke<Report>("import_csv", { table, csvText: text });
      setReport(rep);
      onImported();
    } catch (err) {
      setReport({ inserted: 0, skipped: 0, errors: [String(err)] });
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <button className="ghost" style={{ fontSize: 12, padding: "4px 10px" }} onClick={getTemplate}>
          ↓ Template
        </button>
        <button className="ghost" style={{ fontSize: 12, padding: "4px 10px" }} onClick={doExport}>
          ↓ Export CSV
        </button>
        <label style={{
          cursor: "pointer", fontSize: 12, padding: "4px 10px",
          background: "transparent", border: "1px solid var(--border)",
          borderRadius: 4, color: "var(--text-muted)",
        }}>
          {busy ? "Importing…" : "↑ Import CSV"}
          <input ref={fileRef} type="file" accept=".csv" style={{ display: "none" }} onChange={doImport} />
        </label>
      </div>

      {report && (
        <div style={{
          fontSize: 12, padding: "8px 12px", borderRadius: 4,
          background: report.errors.length > 0 ? "rgba(192,57,43,0.1)" : "rgba(39,174,96,0.1)",
          border: `1px solid ${report.errors.length > 0 ? "var(--danger)" : "var(--success)"}`,
        }}>
          <div>{report.inserted} inserted, {report.skipped} skipped</div>
          {report.errors.map((e, i) => (
            <div key={i} style={{ color: "var(--danger)", marginTop: 2 }}>{e}</div>
          ))}
        </div>
      )}
    </div>
  );
}
